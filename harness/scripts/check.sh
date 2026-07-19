#!/bin/bash
# harness/scripts/check.sh
# 用途：精简后每次 commit 前自动跑 4 条 grep 兜底（PR-Gate 补充项）
# A 档：6 字段 frontmatter 校验（保留 adr_refs）
# 入口：pre-commit hook 或 .github/workflows/harness-ci.yml

set -e

PASS=0
FAIL=0
WARN=0

ok()   { echo "  [OK]   $*"; PASS=$((PASS+1)); }
fail() { echo "  [FAIL] $*"; FAIL=$((FAIL+1)); }
warn() { echo "  [WARN] $*"; WARN=$((WARN+1)); }

# ------------------------------------------------------------
# 1/4 R-2 红线：agents/harness/ 禁业务阈值硬编码
# ------------------------------------------------------------
echo "[1/4] 验证 R-2 红线（agents/harness/ 禁业务阈值硬编码）"
if grep -RnE '(if|return).*score.*[<>]=.*0\.[0-9]+' agents/harness/ 2>/dev/null; then
  fail "agents/harness/ 内出现业务阈值硬编码（违反 R-2）"
  exit 2
else
  ok "R-2 红线无命中"
fi

# ------------------------------------------------------------
# 2/4 harness/ 核心骨架文件数 = 13（A 档）
# ------------------------------------------------------------
echo "[2/4] 验证 harness/ 核心骨架文件数 = 13"
# 核心骨架：4 模板 + 1 context + 1 README + 1 GAP + 1 workflow + 1 state + 1 evidence/README + 1 check.sh + 3 .gitkeep（context/evidence/state）= 13
EXPECTED=13
total=$(find harness/ -type f \
  \( -name '*.md' -o -name '*.yaml' -o -name '*.json' -o -name '*.sh' -o -name '.gitkeep' \) \
  ! -path 'harness/atdd/*' \
  ! -path 'harness/.archive/*' \
  | wc -l)
if [ "$total" -gt "$EXPECTED" ]; then
  warn "harness/ 核心骨架 $total 超过 $EXPECTED（精简目标）"
else
  ok "核心骨架 $total ≤ $EXPECTED"
fi

# ------------------------------------------------------------
# 3/4 SKILL.md 行数 ≤ 100（精简后约束）
# ------------------------------------------------------------
echo "[3/4] 验证 SKILL.md 行数 ≤ 100"
skill_fail=0
for f in .cursor/skills/harness-*/SKILL.md; do
  [ -f "$f" ] || continue
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 100 ]; then
    fail "$f 行数 $lines 超过 100（精简目标）"
    skill_fail=1
  else
    ok "$f 行数 $lines ≤ 100"
  fi
done
if [ "$skill_fail" -eq 1 ]; then
  exit 2
fi

# ------------------------------------------------------------
# 4/4 evidence frontmatter 6 字段齐全（A 档：合并 reviewer_role + author_agent，保留 adr_refs）
# ------------------------------------------------------------
echo "[4/4] 验证 evidence frontmatter 6 字段齐全"
field_fail=0
for f in harness/evidence/*.md; do
  [ -f "$f" ] || continue
  for field in phase run_id role fr_refs adr_refs signed; do
    if ! grep -q "^${field}:" "$f"; then
      fail "$f 缺少字段 ${field}"
      field_fail=1
    fi
  done
done
if [ "$field_fail" -eq 1 ]; then
  exit 2
fi
ok "evidence 6 字段校验通过"

# ------------------------------------------------------------
echo ""
echo "=== Harness check.sh 汇总 ==="
echo "PASS: $PASS | FAIL: $FAIL | WARN: $WARN"
if [ "$FAIL" -gt 0 ]; then
  echo "STATUS: FAIL"
  exit 2
else
  echo "STATUS: OK"
fi
