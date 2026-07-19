#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_phase.py — 跨平台 phase exit_criteria 判定脚本.

真源：harness/checklist.md W4 P4 §5.5.1
配套：agents/harness/DISPATCHER.md §三.b、exit_criteria 真实判定逻辑

解决问题：原 workflow-v2.yaml 的 exit_criteria 是 bash 语法（test/grep/awk），
         Windows PowerShell 环境无法直接执行。本脚本用 Python 解析 YAML + 用
         shlex 解析 shell 命令 + subprocess 跨平台执行 + 解析结果。

支持：
  - python check_phase.py <phase_id>          # 判定单个 phase
  - python check_phase.py --all               # 判定所有 phase 状态
  - python check_phase.py --list              # 列出所有 phase + 当前状态
  - python check_phase.py --phase-id PRD --verbose # 详细输出每条命令结果

退出码：
  0 = 全部 PASS
  1 = 任一 FAIL
  2 = 解析错误（YAML/参数错误）

跨平台：
  - Windows PowerShell / WSL bash / macOS bash / Linux bash 全部可用
  - 不依赖 bash/grep/test，仅用 Python 标准库
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("[FAIL] 需要 PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = PROJECT_ROOT / "harness" / "workflow-v2.yaml"


def load_workflow() -> dict[str, Any]:
    """加载 workflow-v2.yaml."""
    if not WORKFLOW_PATH.exists():
        print(f"[FAIL] 找不到 workflow 文件: {WORKFLOW_PATH}", file=sys.stderr)
        sys.exit(2)
    with WORKFLOW_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_phase(workflow: dict, phase_id: str) -> dict[str, Any]:
    """查找指定 phase 定义."""
    for p in workflow.get("phases", []):
        if p["id"] == phase_id:
            return p
    raise ValueError(f"phase_id '{phase_id}' 不在 workflow-v2.yaml 中")


def _builtin_test(args: list[str], cwd: Path) -> tuple[int, str]:
    """实现 bash 'test' 内置命令的 Python 版本（POSIX 兼容子集）.

    支持的表达式：
      - test -f FILE : FILE 是普通文件
      - test -d DIR  : DIR 是目录
      - test -e PATH : PATH 存在
      - test -s FILE : FILE 存在且大小 > 0
      - test -r FILE : FILE 可读（Windows 下粗略实现）
      - test STR1 = STR2 : 字符串相等
      - test STR1 != STR2 : 字符串不等

    Returns:
        (returncode, stderr): 0 表示 PASS, 1 表示 FAIL
    """
    if not args:
        return 1, "test: missing argument"

    # 一元操作
    if args[0] == "-f" and len(args) == 2:
        return (0, "") if Path(args[1]).is_file() else (1, "")
    if args[0] == "-d" and len(args) == 2:
        return (0, "") if Path(args[1]).is_dir() else (1, "")
    if args[0] == "-e" and len(args) == 2:
        return (0, "") if Path(args[1]).exists() else (1, "")
    if args[0] == "-s" and len(args) == 2:
        p = Path(args[1])
        return (0, "") if (p.is_file() and p.stat().st_size > 0) else (1, "")
    if args[0] == "-r" and len(args) == 2:
        return (0, "") if Path(args[1]).is_file() else (1, "")

    # 二元表达式
    if len(args) == 3 and args[1] == "=":
        return (0, "") if args[0] == args[2] else (1, "")
    if len(args) == 3 and args[1] == "!=":
        return (0, "") if args[0] != args[2] else (1, "")

    return 2, f"test: unsupported expression: {' '.join(args)}"


def _builtin_grep(args: list[str], cwd: Path, stdin: str = "") -> tuple[int, str]:
    """实现 bash 'grep' 内置的 Python 版本（POSIX 兼容子集）.

    支持：
      - grep -q PATTERN FILE         : 找到匹配则 exit 0（静默）
      - grep -qE PATTERN FILE        : -E 表示 extended regex
      - grep -E PATTERN FILE         : 打印匹配行
      - grep PATTERN FILE            : 基础 grep

    Returns:
        (returncode, output): 0=找到匹配, 1=未找到, 2=错误
    """
    import re

    # 解析参数
    quiet = False
    extended_regex = False
    pattern = None
    files = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "-q":
            quiet = True
            i += 1
        elif a == "-E":
            extended_regex = True
            i += 1
        elif a.startswith("-"):
            # 忽略其他 flag（简化）
            i += 1
        else:
            if pattern is None:
                pattern = a
            else:
                files.append(a)
            i += 1

    if pattern is None:
        return 2, "grep: missing pattern"

    flags = re.IGNORECASE  # 默认大小写敏感先不管
    if extended_regex:
        regex_flags = re.IGNORECASE if "-i" in args else 0
    else:
        regex_flags = 0

    # 编译正则
    try:
        rgx = re.compile(pattern, regex_flags)
    except re.error as e:
        return 2, f"grep: regex error: {e}"

    # 读取输入
    if not files:
        # 从 stdin 读
        content = stdin
    elif len(files) == 1:
        fp = Path(files[0])
        if not fp.is_file():
            return 2, f"grep: {files[0]}: No such file"
        content = fp.read_text(encoding="utf-8", errors="replace")
    else:
        # 多文件模式（简化：合并）
        parts = []
        for f in files:
            fp = Path(f)
            if fp.is_file():
                parts.append(fp.read_text(encoding="utf-8", errors="replace"))
        content = "\n".join(parts)

    matches = rgx.findall(content)
    if not matches:
        return 1, ""
    if quiet:
        return 0, ""
    # 非 quiet：返回匹配的第一个
    return 0, (matches[0] if isinstance(matches[0], str) else "\n".join(matches[0]))[:200]


def run_exit_criterion(cmd: str, cwd: Path) -> tuple[bool, str]:
    """执行单条 exit_criteria 命令，返回 (pass, message).

    支持的语法（POSIX 子集）：
      - test -f/-d/-e/-s/-r PATH
      - grep -q/-qE/-E PATTERN FILE
      - 其他命令 fallback 到 subprocess

    Args:
        cmd: shell 命令字符串（如 'test -f harness/evidence/01-requirement.md'）
        cwd: 工作目录

    Returns:
        (True, "PASS: ..."): 命令成功
        (False, "FAIL: ..."): 命令失败
    """
    try:
        cmd_parts = shlex.split(cmd, posix=(os.name != "nt"))
    except ValueError:
        cmd_parts = cmd.split()

    if not cmd_parts:
        return False, f"EMPTY: {cmd}"

    prog = cmd_parts[0]
    args = cmd_parts[1:]

    # Bash 内置命令：test / [
    if prog in ("test", "["):
        rc, stderr = _builtin_test(args, cwd)
        if rc == 0:
            return True, f"PASS (rc=0): {cmd}"
        return False, f"FAIL (rc={rc}): {cmd}" + (f" | {stderr}" if stderr else "")

    # bash builtin: grep
    if prog == "grep" or prog.endswith("/grep") or prog == "/usr/bin/grep":
        rc, output = _builtin_grep(args, cwd)
        if rc == 0:
            return True, f"PASS (rc=0): {cmd}"
        return False, f"FAIL (rc={rc}): {cmd}" + (f" | {output}" if output else "")

    # 兜底：subprocess 跨平台执行
    try:
        result = subprocess.run(
            cmd_parts,
            cwd=str(cwd),
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError as e:
        return False, f"NOT FOUND: {cmd} ({e})"
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after 10s: {cmd}"
    except Exception as e:
        return False, f"ERROR: {cmd} ({type(e).__name__}: {e})"

    if result.returncode == 0:
        return True, f"PASS (rc=0): {cmd}"
    return False, f"FAIL (rc={result.returncode}): {cmd} | stderr={result.stderr.strip()[:200]}"


def check_phase(phase_id: str, workflow: dict, verbose: bool = False) -> bool:
    """检查指定 phase 的所有 exit_criteria.

    Returns:
        True = 全部 PASS, False = 任一 FAIL
    """
    try:
        phase = find_phase(workflow, phase_id)
    except ValueError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return False

    exit_criteria = phase.get("exit_criteria", [])
    if not exit_criteria:
        print(f"[WARN] phase '{phase_id}' 无 exit_criteria 定义，默认 PASS")
        return True

    print(f"[INFO] 检查 phase={phase_id}，{len(exit_criteria)} 条 exit_criteria")

    all_pass = True
    for i, cmd in enumerate(exit_criteria, 1):
        ok, msg = run_exit_criterion(cmd, PROJECT_ROOT)
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status} [{i}/{len(exit_criteria)}] {msg}")
        if not ok:
            all_pass = False
            if not verbose:
                # 非 verbose 模式：第一次 FAIL 后立即退出
                break

    if all_pass:
        print(f"[PASS] phase={phase_id} 全部 exit_criteria 满足")
    else:
        print(f"[FAIL] phase={phase_id} 存在未满足的 exit_criteria")
    return all_pass


def list_all_phases(workflow: dict) -> None:
    """列出所有 phase + 数量统计."""
    phases = workflow.get("phases", [])
    print(f"\nworkflow-v2.yaml 共定义 {len(phases)} 个 phase：\n")
    for p in phases:
        n_criteria = len(p.get("exit_criteria", []))
        auto = "auto" if p.get("auto_mode") else "manual"
        print(f"  - {p['id']:20s} ({auto:6s}) entry={p['entry_agent']:25s} exit_criteria={n_criteria}")
    print()


def check_all_phases(workflow: dict) -> bool:
    """检查所有 phase 状态."""
    results: dict[str, bool] = {}
    for p in workflow.get("phases", []):
        phase_id = p["id"]
        results[phase_id] = check_phase(phase_id, workflow, verbose=False)
        print()  # 空行分隔

    # 输出汇总
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print("=" * 60)
    print(f"[SUMMARY] {passed}/{total} phase 满足 exit_criteria")
    for phase_id, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {status:6s} {phase_id}")
    print("=" * 60)
    return passed == total


def main() -> int:
    parser = argparse.ArgumentParser(description="跨平台 phase exit_criteria 判定")
    parser.add_argument("phase_id", nargs="?", help="phase ID（如 PRD）")
    parser.add_argument("--all", action="store_true", help="检查所有 phase")
    parser.add_argument("--list", action="store_true", help="列出所有 phase")
    parser.add_argument("--verbose", action="store_true", help="显示每条命令结果")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    workflow = load_workflow()

    if args.json:
        # 输出 JSON 供 CI 解析
        output = {
            "phases": [
                {
                    "id": p["id"],
                    "entry_agent": p.get("entry_agent"),
                    "exit_criteria_count": len(p.get("exit_criteria", [])),
                    "auto_mode": p.get("auto_mode", False),
                }
                for p in workflow.get("phases", [])
            ]
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    if args.list:
        list_all_phases(workflow)
        return 0

    if args.all:
        ok = check_all_phases(workflow)
        return 0 if ok else 1

    if args.phase_id:
        ok = check_phase(args.phase_id, workflow, verbose=args.verbose)
        return 0 if ok else 1

    # 默认行为：列出 + 检查 PRD（最常见的入口）
    print("[INFO] 未指定 phase，显示所有 phase 列表：")
    list_all_phases(workflow)
    print("[INFO] 用法：")
    print("  python check_phase.py <phase_id>     # 检查单个 phase")
    print("  python check_phase.py --all          # 检查所有 phase")
    print("  python check_phase.py --list         # 仅列出")
    print("  python check_phase.py --json         # JSON 输出")
    return 0


if __name__ == "__main__":
    sys.exit(main())