"""4 项验证：唯一真源自检 / 真源存在性 / CI Gate 9 / 反向引用。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path("d:/agent-project/SelfwellAgent")


def run(cmd: str, cwd: str | None = None) -> tuple[int, str]:
    """Run a shell command and return (exit_code, output)."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd or str(ROOT),
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


results: dict[str, str] = {}

# === 验证 1: 唯一真源自检（除真源外其他文档不应再有"完整 DDD 目录树"） ===
section("验证 1: 唯一真源自检")
# 标准: 找含 contexts/ 且含 domain/ 且含 application/ 的文件
cmd1 = (
    'grep -rln "contexts/" .cursor/rules/ docs/architecture/ 2>/dev/null '
    '| grep -v ddd-bounded-context.mdc '
    '| xargs -I{} grep -l "domain/" {} 2>/dev/null '
    '| xargs -I{} grep -l "application/" {} 2>/dev/null'
)
code1, out1 = run(cmd1)
if code1 != 0 or not out1.strip():
    print("PASS: 除真源外 0 命中（无完整 DDD 目录树）")
    results["v1"] = "PASS"
else:
    print(f"FAIL: 命中文件:\n{out1}")
    results["v1"] = f"FAIL:\n{out1}"

# === 验证 2: 真源存在性自检 ===
section("验证 2: 真源存在性自检")
source_file = ROOT / ".cursor/rules/ddd-bounded-context.mdc"
if not source_file.exists():
    print("FAIL: 真源文件不存在")
    results["v2"] = "FAIL: file missing"
    sys.exit(1)
content = source_file.read_text(encoding="utf-8")
mark = "本节是后端目录的唯一真源"
count = content.count(mark)
if count == 1:
    print(f"PASS: 真源标识符出现 {count} 次")
    results["v2"] = "PASS"
else:
    print(f"FAIL: 真源标识符 '{mark}' 出现 {count} 次（期望 1）")
    results["v2"] = f"FAIL: count={count}"

# === 验证 3: CI Gate 9 仍生效 ===
section("验证 3: CI Gate 9 仍生效")
ci_file = ROOT / ".github/workflows/pr-gate-ci.yml"
if not ci_file.exists():
    print("FAIL: CI workflow 文件不存在")
    results["v3"] = "FAIL: file missing"
else:
    ci_content = ci_file.read_text(encoding="utf-8")
    if "Gate 9" in ci_content and "ddd-bounded-context.mdc" in ci_content:
        # 抽取 Gate 9 上下文
        lines = ci_content.splitlines()
        for i, line in enumerate(lines):
            if "Gate 9" in line or "ddd-bounded-context.mdc" in line:
                ctx = "\n".join(lines[max(0, i - 1) : min(len(lines), i + 5)])
                print(f"匹配: {ctx}")
        results["v3"] = "PASS"
    else:
        print("WARN: Gate 9 或 ddd-bounded-context.mdc 未同时出现")
        results["v3"] = "WARN"

# === 验证 4: 引用真源的反向链（纯 Python 扫描，绕过 PS 5.x 编码层） ===
section("验证 4: 引用真源的反向链")
target_token = "ddd-bounded-context.mdc"
search_dirs = [ROOT / ".cursor/rules", ROOT / "docs/architecture"]
matched_files: list[str] = []
for sd in search_dirs:
    if not sd.exists():
        continue
    for f in sd.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix in {".md", ".mdc", ".yml", ".yaml"}:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                if target_token in content:
                    matched_files.append(str(f.relative_to(ROOT)))
            except Exception:
                pass
matched_files.sort()
print(f"反向引用文件数: {len(matched_files)}")
for f in matched_files:
    print(f"  - {f}")
if len(matched_files) >= 5:
    print("PASS: >= 5 个文件引用真源")
    results["v4"] = "PASS"
else:
    print(f"FAIL: 仅 {len(matched_files)} 个文件引用真源（期望 >= 5）")
    results["v4"] = f"FAIL: {len(matched_files)} files"

# === 汇总 ===
section("汇总")
for k, v in results.items():
    if v == "PASS":
        icon = "[OK]"
    elif v.startswith("WARN"):
        icon = "[WARN]"
    else:
        icon = "[FAIL]"
    print(f"  {icon} {k}: {v}")

if all(v == "PASS" for v in results.values()):
    print("\nALL 4 CHECKS PASSED")
    sys.exit(0)
else:
    print("\nSOME CHECKS FAILED")
    sys.exit(1)
