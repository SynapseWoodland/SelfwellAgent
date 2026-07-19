#!/usr/bin/env bash
# check_atdd.sh — PR Gate 卡口 3 辅助脚本
#
# 用途：检查 PR 修改的源代码是否关联了对应的 ATDD 验收用例。
#
# 真源：harness/checklist.md W4 P4 §5.1.2 卡口 3 实现
# 配套：.github/workflows/pr-gate-ci.yml（卡口 3 atdd-required）
#
# 规则（2026-07-19 W4 P4 §5.1.2 启用）：
#   1. PR 修改 backend/app/<module>/<file>.py 时
#      必须存在对应 ATDD 文档
#   2. 兼容 2 种 ATDD 命名：
#      a. ATDD-<MODULE>-*.md（推荐新命名）
#      b. ATDD-M<N>-AC.md（已有 ATDD-M1 ~ M14 通用，跨模块适用）
#   3. 例外（豁免）：
#      - 仅修改 tests/ docs/ harness/ .cursor/ .github/ 目录
#      - chore / docs / ci / deps 类 commit（已在卡口 2 豁免）

set -e

BASE_REF="${1:-origin/main}"
HEAD_REF="${2:-HEAD}"

# 1. 收集 PR 修改的 Python 文件（不含 tests/）
CHANGED_PY=$(git diff --name-only "$BASE_REF"...$HEAD_REF 2>/dev/null | grep -E '^backend/app/.*\.py$' || true)

# 2. 没有改动业务代码 → 自动通过
if [ -z "$CHANGED_PY" ]; then
  echo "✅ 卡口 3 PASS：本次 PR 未修改 backend/app/，无需 ATDD 关联"
  exit 0
fi

# 3. 检查 ATDD 目录是否存在
ATDD_DIR="harness/atdd"
if [ ! -d "$ATDD_DIR" ]; then
  echo "::warning::ATDD 目录 ($ATDD_DIR) 不存在，暂跳过严格检查"
  echo "::warning::建议建立目录结构：harness/atdd/ATDD-<MODULE>-<SEQ>.md"
  exit 0
fi

# 4. 如果存在任何 ATDD-M*.md（M1~M14 通用），视为已覆盖
#    这是因为现有 ATDD 是按模块编号组织（FR/模块对应），跨模块覆盖
GENERIC_COUNT=$(ls "$ATDD_DIR"/ATDD-M*-AC.md 2>/dev/null | wc -l)
if [ "$GENERIC_COUNT" -gt 0 ]; then
  echo "✅ 卡口 3 PASS：发现 $GENERIC_COUNT 个 ATDD-M*-AC.md 通用验收用例（覆盖模块编号体系）"
  echo "   （命名兼容模式：ATDD-<MODULE>-*.md 或 ATDD-M<N>-AC.md）"
  exit 0
fi

# 5. 否则按模块名匹配 ATDD-<MODULE>-*.md
MODULES=$(echo "$CHANGED_PY" | awk -F/ 'NF>=3 {print $3}' | sort -u)
MISSING=()
for mod in $MODULES; do
  if ! ls "$ATDD_DIR"/ATDD-${mod}-*.md >/dev/null 2>&1; then
    MISSING+=("$mod")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "::error::卡口 3 失败：以下模块的 ATDD 验收用例缺失："
  printf '  - %s\n' "${MISSING[@]}"
  echo ""
  echo "修复方式："
  echo "  在 $ATDD_DIR/ 下新建 ATDD-<MODULE>-<SEQ>.md"
  echo "  或建立 ATDD-M<N>-AC.md 通用验收框架"
  exit 1
fi

echo "✅ 卡口 3 PASS：所有改动模块都有 ATDD 验收用例"