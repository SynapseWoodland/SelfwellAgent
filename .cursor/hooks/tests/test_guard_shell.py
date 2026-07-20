"""tests/test_guard_shell.py — guard-shell.py v4 单元测试

测试目标：
  - 违规命令 → permission=deny（exit 0 或 exit 2）
  - 正常命令 → permission=allow
  - 解析失败 → fail-open allow
  - 白名单命令 → 直接放行

运行：python -m pytest .cursor/hooks/tests/test_guard_shell.py -v
或：  python -m unittest discover .cursor/hooks/tests

详见：.cursor/hooks/README.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

HOOK_DIR = Path(__file__).resolve().parent.parent  # .cursor/hooks/
PY_SCRIPT = HOOK_DIR / "guard-shell.py"
PS_SCRIPT = HOOK_DIR / "guard-shell.ps1"

# 集成测试要求 python 在 PATH 上
PYTHON_EXE = sys.executable  # 当前 Python 解释器


# ---------------------------------------------------------------------------
# 子进程 helper
# ---------------------------------------------------------------------------


def _run_hook(payload: dict, timeout: float = 5.0) -> tuple[int, str, str]:
    """调用 guard-shell.py 子进程，返回 (returncode, stdout, stderr)。"""
    proc = subprocess.run(
        [PYTHON_EXE, str(PY_SCRIPT)],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# 单元测试 — 通过子进程跑完整 stdin/stdout JSON 协议
# ---------------------------------------------------------------------------


class TestViolationsShouldDeny:
    """违规命令必须被 deny。"""

    @pytest.mark.parametrize(
        "command",
        [
            # 文件读取类
            "cat .cursorrules",
            "cat backend/app/main.py",
            "cat .cursor/rules/file-operation-stability.mdc",
            "head README.md",
            "tail backend/app/main.py",
            "more notes.txt",
            "less file.log",
            "type README.md",
            # 文件修改类
            "sed -i 's/foo/bar/' file.txt",
            "sed 's/foo/bar/' file.txt",
            "awk '{print $1}' file.txt",
            "perl -pi -e 's/foo/bar/' file.txt",
            # 文件写入类
            "echo hello > out.txt",
            "printf '%s\\n' hi > out.txt",
            "cat file > out.txt",
            "echo hi | tee out.txt",
            # 高危命令
            "rm -rf /",
            "rm -rf /etc",
            # 跨盘列目录
            "dir /b C:\\Users",
            'cmd /c "dir C:\\Windows"',
            # PS 反射读字节
            "powershell -Command [System.IO.File]::ReadAllText('foo.txt')",
            # PowerShell 文件写入（GBK/UTF-16 编码问题）
            "Set-Content -Path file.txt -Value '中文内容'",
            "Out-File -FilePath output.txt",
            "powershell -Command Set-Content -Path foo.txt -Value test",
            # PowerShell -File 脚本执行
            "powershell -File run_fix.ps1",
            "pwsh -File script.ps1",
            # git checkout -- 恢复暂存区
            "git checkout -- .",
            "git checkout -- file.txt",
        ],
    )
    def test_violation_denied(self, command: str) -> None:
        code, stdout, stderr = _run_hook({"command": command, "cwd": "."})
        assert code in (0, 2), f"期望 exit 0 或 2，实际 {code}。stderr={stderr}"
        assert stdout.strip(), "stdout 必须有 JSON 输出"
        resp = json.loads(stdout.strip())
        assert resp["permission"] == "deny", (
            f"违规命令未被 deny: {command}\n响应: {resp}"
        )


class TestNormalCommandsShouldAllow:
    """正常命令必须被 allow。"""

    @pytest.mark.parametrize(
        "command",
        [
            # 白名单命令
            "git status",
            "git log --oneline -5",
            "git --no-pager diff",
            "ls -la",
            "dir",
            "pwd",
            "echo hello",  # echo 不带重定向 = 安全
            "echo $PATH",
            "Get-ChildItem .",
            "Get-Location",
            "tree",
            "find . -name '*.py'",
            # 其他合规命令（git commit / npm run / python / curl 等）
            "git commit -m 'test'",
            "git push origin main",
            "python -m pytest",
            "python3 script.py",
            "npm install",
            "npm run lint",
            "curl https://api.example.com",
            "wget https://example.com/file.zip",
        ],
    )
    def test_normal_allowed(self, command: str) -> None:
        code, stdout, stderr = _run_hook({"command": command, "cwd": "."})
        assert code == 0, f"期望 exit 0，实际 {code}。stderr={stderr}"
        assert stdout.strip(), "stdout 必须有 JSON 输出"
        resp = json.loads(stdout.strip())
        assert resp["permission"] == "allow", (
            f"正常命令被误拦: {command}\n响应: {resp}"
        )


class TestFailOpenBehaviors:
    """异常输入必须 fail-open（绝不让 hook bug 阻塞所有 shell）。"""

    def test_empty_stdin_allows(self) -> None:
        """stdin 为空 → 放行。"""
        proc = subprocess.run(
            [PYTHON_EXE, str(PY_SCRIPT)],
            input="",
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert proc.returncode == 0
        resp = json.loads(proc.stdout.strip())
        assert resp["permission"] == "allow"

    def test_invalid_json_allows(self) -> None:
        """JSON 损坏 → 放行。"""
        proc = subprocess.run(
            [PYTHON_EXE, str(PY_SCRIPT)],
            input="not json at all",
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert proc.returncode == 0
        resp = json.loads(proc.stdout.strip())
        assert resp["permission"] == "allow"

    def test_empty_command_allows(self) -> None:
        """command 字段为空 → 放行。"""
        code, stdout, _ = _run_hook({"command": "", "cwd": "."})
        assert code == 0
        resp = json.loads(stdout.strip())
        assert resp["permission"] == "allow"

    def test_missing_command_field_allows(self) -> None:
        """没有 command 字段 → 放行。"""
        code, stdout, _ = _run_hook({"cwd": "."})
        assert code == 0
        resp = json.loads(stdout.strip())
        assert resp["permission"] == "allow"


class TestWhitelistFastPath:
    """白名单命令不应被违规检测触及。"""

    def test_git_command_passes_quick(self) -> None:
        """git 命令应该走白名单快速通道。"""
        code, stdout, _ = _run_hook({"command": "git status"})
        assert code == 0
        resp = json.loads(stdout.strip())
        assert resp["permission"] == "allow"

    def test_ls_with_path_passes(self) -> None:
        """ls 带路径应放行。"""
        code, stdout, _ = _run_hook({"command": "ls -la /tmp"})
        assert code == 0
        resp = json.loads(stdout.strip())
        assert resp["permission"] == "allow"


class TestCommandCmdFallback:
    """测试 .cmd 垫片存在性（Windows 专属，不在此处运行，只检查文件）。"""

    def test_cmd_wrapper_exists(self) -> None:
        assert (HOOK_DIR / "guard-shell.cmd").exists(), "guard-shell.cmd 必须存在"

    def test_py_script_exists(self) -> None:
        assert PY_SCRIPT.exists(), "guard-shell.py 必须存在"

    def test_ps_fallback_exists(self) -> None:
        assert PS_SCRIPT.exists(), "guard-shell.ps1 (v3 fallback) 必须存在"