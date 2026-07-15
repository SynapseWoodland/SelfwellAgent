#!/usr/bin/env python3
"""guard-shell.py — Cursor beforeShellExecution hook (v4 / Python)

拦截违反 .cursor/rules/file-operation-stability.mdc 的 shell 命令。

Cursor Hooks 协议契约（2026-07-15）：
  - stdin:  JSON { "command": str, "cwd": str, ... }
  - stdout: JSON { "permission": "allow"|"deny", "user_message"?, "agent_message"? }
  - exit 0: 走 stdout JSON；exit 2: 等价于 deny（不需要 JSON）
  - 其他 exit code: hook 失败，按 failClosed 配置决定行为

v4 vs v3 修复要点：
  - 用 Python stdlib（json/re/sys/pathlib/shlex/signal）替换 PowerShell，
    避免 pwsh + Cursor 沙箱下 "no output" 错判阻塞
  - stdin JSON 解析 + 显式 stdout flush（双重保险防止 buffering 丢输出）
  - 4s 软超时（hooks.json 设 5s 总超时）：自身 bug 不能拖垮 agent
  - 解析失败时 fail-open：只输出 permission=allow，绝不因 hook 自身问题
    阻塞所有 shell（这会导致 agent 完全瘫痪）

本脚本只做违规检查；与 hook v3 行为对等：
  - 命中违规 → permission=deny + exit 0
  - 备选：直接 exit 2（无需 stdout）

详见：.cursor/hooks/README.md
"""

from __future__ import annotations

import json
import re
import shlex
import signal
import sys
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# 0. 配置常量（与 .cursor/rules/file-operation-stability.mdc 红线一一对应）
# ---------------------------------------------------------------------------

# 白名单：这些命令不修改文件、不删根、不读文件 → 快速放行
WHITELIST: Final[frozenset[str]] = frozenset(
    {
        "git",
        "ls",
        "dir",          # Windows cmd 内置列目录
        "pwd",
        "cd",
        "echo",         # 仅 echo 不带 > 才安全；带 > 走违规检查
        "pwd",
        "cd",
        "whoami",
        "date",
        "hostname",
        "clear",
        "cls",
        "where",        # Windows cmd 内置
        "which",        # unix
        "Get-ChildItem",
        "Get-Item",
        "Get-Location",
        "Test-Path",
        "Select-Object",
        "Format-List",
        "Format-Table",
        "Measure-Object",
        "tree",
        "find",
    }
)

# PowerShell / cmd 别名补全（仅允许这些别名；其他别名会被 shlex 拆词后走违规检查）
SAFE_POWERSHELL_ALIASES: Final[frozenset[str]] = frozenset(
    {"ls", "dir", "pwd", "cat", "cp", "mv", "rm", "echo", "clear", "cls"}
)
# ↑ 但即便 cat/cp/mv/rm 在白名单别名里，仍有违规风险，所以实际不列入放行集合。
#    保留字段供未来扩展用。

# 违规模式（与 file-operation-stability.mdc 红线一一对应）
VIOLATIONS: Final[tuple[tuple[re.Pattern[str], str, str], ...]] = (
    # ---------- 文件读取类违规（应用 Read 工具） ----------
    # 注：\S 匹配任意非空白字符，覆盖所有文件路径（含 .cursorrules / .gitignore / 无扩展名）
    (
        re.compile(r"(?<![\w/])\bcat\s+\S"),
        "shell cat 读文件 — 应改用 Read 工具",
        "Read",
    ),
    (
        re.compile(r"(?<![\w/])\bhead\s+\S"),
        "shell head 读文件 — 应改用 Read 工具",
        "Read",
    ),
    (
        re.compile(r"(?<![\w/])\btail\s+\S"),
        "shell tail 读文件 — 应改用 Read 工具",
        "Read",
    ),
    (
        re.compile(r"(?<![\w/])\bmore\s+\S"),
        "shell more 读文件 — 应改用 Read 工具",
        "Read",
    ),
    (
        re.compile(r"(?<![\w/])\ble\s+\S"),
        "shell less 读文件 — 应改用 Read 工具",
        "Read",
    ),
    (
        re.compile(r"(?<![\w/])\btype\s+\S"),
        "cmd type 读文件 — 应改用 Read 工具",
        "Read",
    ),
    (
        re.compile(r"(?<![\w/])\bGet-Content\s+\S"),
        "PowerShell Get-Content 读文件 — 应改用 Read 工具",
        "Read",
    ),
    # ---------- 文件修改类违规（应用 StrReplace / Write 工具） ----------
    (re.compile(r"(?<![\w/])\bsed\s+-i"), "sed -i 原地修改文件 — 绝对禁止", "StrReplace/Write"),
    (re.compile(r"(?<![\w/])\bsed\s+"), "sed 修改文件 — 绝对禁止", "StrReplace/Write"),
    (re.compile(r"(?<![\w/])\bawk\s+"), "awk 处理文件 — 绝对禁止", "StrReplace/Write"),
    (
        re.compile(r"(?<![\w/])\bperl\s+-?pi?e?\s+"),
        "perl -pi 修改文件 — 绝对禁止",
        "StrReplace/Write",
    ),
    # ---------- 文件写入类违规（应用 Write 工具） ----------
    (
        re.compile(r"(?<![\w/])\becho\s+[^|]*>\s*\S"),
        "echo 重定向写文件 — 应用 Write 工具",
        "Write",
    ),
    (
        re.compile(r"(?<![\w/])\bprintf\s+[^|]*>\s*\S"),
        "printf 重定向写文件 — 应用 Write 工具",
        "Write",
    ),
    (re.compile(r"\bcat\s+-?>"), "cat 重定向 — 应用 Write/Read 工具", "Write"),
    (re.compile(r"\btee\s+"), "tee 写入文件 — 应用 Write 工具", "Write"),
    # ---------- 高危命令 ----------
    (
        re.compile(r"\brm\s+-rf?\s+/"),
        "rm -rf 删根 — 高危命令，需用户书面授权",
        "需用户授权",
    ),
    # ---------- 跨盘 / 跨 shell 列目录（应用 Glob 工具） ----------
    (
        re.compile(r"(?<![\w/])\bdir\s+/[a-z]\s+\S+"),
        "用 cmd 跨盘列目录 — 权限不对等，建议用 Glob 工具",
        "Glob",
    ),
    (
        re.compile(r"^cmd\s+/c\s+\"dir\s+"),
        'cmd /c "dir ..." 列表 — 用 Glob 工具替代',
        "Glob",
    ),
    # ---------- PowerShell 反射读字节 ----------
    (
        re.compile(r"(?i)\bpowershell?(?:\.exe)?\s+-Command\s+.*\[System\.IO\.File\]"),
        "用 PowerShell [IO.File] 读文件 — 应用 Read 工具",
        "Read",
    ),
)


# ---------------------------------------------------------------------------
# 1. 工具函数
# ---------------------------------------------------------------------------


def _emit(response: dict) -> None:
    """输出 JSON 到 stdout 并 flush（防 Cursor 沙箱 buffering 丢输出）。"""
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _deny(reason: str, command: str, replacement: str) -> None:
    """违规 → deny。"""
    _emit(
        {
            "permission": "deny",
            "user_message": (
                f"[file-operation-stability.mdc 拦截] {reason}。命令: {command}"
            ),
            "agent_message": (
                f"SHELL COMMAND BLOCKED by .cursor/hooks/guard-shell.py (v4)\n\n"
                f"Reason: {reason}\n"
                f"Command: {command}\n\n"
                f"修复方案：用 Cursor 的 {replacement} 工具替代。\n"
                f"详见 .cursor/rules/file-operation-stability.mdc"
            ),
        }
    )
    # 双重保险：permission=deny 同时 exit 2（即使 stdout 被截也能阻塞）
    sys.exit(2)


def _allow() -> None:
    """放行。"""
    _emit({"permission": "allow"})
    sys.exit(0)


def _timeout_handler(_signum, _frame) -> None:
    """4s 软超时：自身 bug 不能拖垮 agent，输出 allow 后退出。"""
    _emit(
        {
            "permission": "allow",
            "user_message": "[guard-shell.py] 内部超时 4s，fail-open 放行",
        }
    )
    sys.exit(0)


# ---------------------------------------------------------------------------
# 2. 违规检测
# ---------------------------------------------------------------------------


def _first_token(command: str) -> str:
    """安全取第一个 token（不依赖 shlex，兼容裸命令）。"""
    s = command.lstrip()
    # 处理引号起始：'(?<!\w)\b' 风格
    if not s:
        return ""
    return s.split(maxsplit=1)[0].strip("\"'")


def _is_safe_redirect_echo(command: str) -> bool:
    """判断 echo 是否带 > 重定向（带就是违规）。"""
    # 简单判：echo 后任意位置出现 > 后接非空白 → 违规
    return bool(re.search(r"(?<![\w/])\becho\s+[^|]*>\s*\S", command))


def _check_violations(command: str) -> tuple[str, str] | None:
    """命中违规返回 (reason, replacement)；否则 None。"""
    for pattern, reason, replacement in VIOLATIONS:
        if pattern.search(command):
            return (reason, replacement)
    return None


# ---------------------------------------------------------------------------
# 3. 主流程
# ---------------------------------------------------------------------------


def main() -> None:
    # 3.0 软超时（Unix only；Windows 无 SIGALRM，跳过）
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(4)
    except (AttributeError, ValueError):
        # Windows: signal.SIGALRM 不存在；靠 hooks.json 的 timeout: 5 兜底
        pass

    # 3.1 读 stdin JSON
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""

    if not raw.strip():
        # 没有输入（hook 没收到 stdin JSON）— fail-open 放行
        # 原因：Cursor 协议在某些情况下可能不传 stdin；
        # fail-closed 会让所有 shell 全瘫痪，无法调试
        _emit({"permission": "allow"})
        return

    # 3.2 解析 JSON
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # JSON 损坏 — fail-open
        _emit({"permission": "allow"})
        return

    command = payload.get("command") or ""
    if not isinstance(command, str) or not command.strip():
        _emit({"permission": "allow"})
        return

    # 3.3 白名单快速通道
    first = _first_token(command)
    if first in WHITELIST:
        # echo 不带 > 才安全（带 > 走违规检查）
        if first == "echo" and _is_safe_redirect_echo(command):
            # echo 带重定向 → 违规
            pass
        else:
            _emit({"permission": "allow"})
            return

    # 3.4 违规检测
    hit = _check_violations(command)
    if hit is not None:
        reason, replacement = hit
        _deny(reason, command, replacement)

    # 3.5 没有命中违规模式 → 放行
    _emit({"permission": "allow"})
    return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # 任何未捕获异常 → fail-open（绝不让 hook bug 阻塞所有 shell）
        sys.stdout.write(
            json.dumps(
                {
                    "permission": "allow",
                    "user_message": f"[guard-shell.py] 内部异常 fail-open: {type(e).__name__}: {e}",
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        sys.stdout.flush()
        sys.exit(0)