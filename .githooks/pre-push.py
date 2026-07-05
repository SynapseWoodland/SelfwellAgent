# -*- mode: python -*-
# ruff: noqa: T201  # hooks 中 print 是合法输出
"""
pre-push hook（V1.3）— git push 前跑 L2-L4 质量门禁（警告式，不阻止 push）

策略：本地失败仅警告（WARN），允许 push；CI 流水线负责拦截
原因：1 人项目 + 紧急修复场景，不阻塞开发流；但提供兜底保障

触发：git push 前
跳过：git push --no-verify
手动跑：python .githooks/pre-push.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LINT_CHECKS: list[tuple[str, list[str], str]] = [
    (
        "L2 — mypy (strict, backend only)",
        ["uv", "run", "mypy", "backend/", "--strict", "--ignore-missing-imports"],
        "类型检查（mypy strict）",
    ),
    (
        "L3 — pytest (backend/tests/, fast only)",
        [
            "uv",
            "run",
            "pytest",
            "backend/tests/",
            "-x",
            "-q",
            "-m",
            "not slow",
            "--no-cov",
        ],
        "单元测试（pytest，标记 -m not slow 跳过慢测）",
    ),
]


def run_check(name: str, cmd: list[str], desc: str) -> bool:
    """执行单个检查；返回 True=通过，False=失败。"""
    print(f"\n→ {name}\n  ({desc})")
    if shutil.which(cmd[0]) is None:
        print(f"  ⚠️  {cmd[0]} 未安装，跳过此检查（请运行: uv sync --all-extras）")
        return True
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ✗ FAIL")
        # 只输出最后 30 行（避免刷屏）
        tail = result.stdout[-2000:] + result.stderr[-2000:]
        print(tail[-2000:])
        return False
    print(f"  ✓ PASS")
    return True


def main() -> int:
    print("=" * 70)
    print("SelfwellAgent pre-push hook（WARN-only 模式）")
    print("=" * 70)

    failures: list[str] = []
    for name, cmd, desc in LINT_CHECKS:
        if not run_check(name, cmd, desc):
            failures.append(name)

    print("\n" + "=" * 70)
    if failures:
        print(f"⚠️  以下 {len(failures)} 项检查失败：")
        for name in failures:
            print(f"  - {name}")
        print()
        print("→ 本地策略：WARN-only，**允许 push**（CI 会再次校验）")
        print("→ 强烈建议先修复再 push，避免 CI 失败")
        print("→ 跳过方式：git push --no-verify")
        return 0  # 警告式：返回 0 允许 push
    print("✅ 所有检查通过，允许 push")
    return 0


if __name__ == "__main__":
    sys.exit(main())