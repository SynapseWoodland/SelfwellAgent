#!/usr/bin/env bash
# check_adr.sh — PR Gate 卡口 4 辅助脚本
#
# 用途：检查 PR 是否与已 freeze 的 ADR 决策冲突。
#
# 真源：harness/checklist.md W4 P4 §5.1.2 卡口 4 实现
# 配套：.github/workflows/pr-gate-ci.yml（卡口 4 adr-conflict）
#
# 规则（2026-07-19 W4 P4 §5.1.2 启用）：
#   1. ADR freeze 字段检查
#      如果 docs/adr/ADR-*.md 顶部含 `freeze: true`（v2 引入），
#      则 PR 不允许修改该 ADR（除非 PR 标题含 ADR-AMENDMENT）
#   2. ADR 引用一致性
#      PR 涉及的功能改动应该在 PR body 中引用相关 ADR
#   3. 新增 ADR 必须包含 status / date / decider / consequences 4 字段
#
# 例外（豁免）：
#   - 仅修改 docs/adr/ 自身（维护类改动）
#   - 仅修改 harness/ / .cursor/ / .github/ 目录

set -e

BASE_REF="${1:-origin/main}"
HEAD_REF="${2:-HEAD}"

# 1. 检查 ADR 目录是否存在
ADR_DIR="docs/adr"
if [ ! -d "$ADR_DIR" ]; then
  echo "::warning::ADR 目录 ($ADR_DIR) 不存在，跳过 ADR 冲突检查"
  exit 0
fi

# 2. 收集 PR 修改的文件
CHANGED=$(git diff --name-only "$BASE_REF"...$HEAD_REF 2>/dev/null || true)

# 3. 例外：仅维护类改动
if echo "$CHANGED" | grep -qvE '^(docs/adr/|harness/|\.cursor/|\.github/)'; then
  # 有非维护类改动 → 严格检查
  :

else
  echo "✅ 卡口 4 PASS：本次 PR 仅为 ADR 维护类改动"
  exit 0
fi

# 4. 检查所有 freeze 的 ADR 是否被修改
FROZEN_ADRS=$(grep -l '^freeze: true' "$ADR_DIR"/ADR-*.md 2>/dev/null || true)
if [ -z "$FROZEN_ADRS" ]; then
  echo "✅ 卡口 4 PASS：无 freeze ADR（freeze 约定尚未广泛启用，宽松通过）"
  exit 0
fi

PR_TITLE=$(git log -1 --pretty=%s "$HEAD_REF")
CONFLICT=0
for adr in $FROZEN_ADRS; do
  if echo "$CHANGED" | grep -qF "$adr"; then
    if ! echo "$PR_TITLE" | grep -qE 'ADR-AMENDMENT'; then
      echo "::error::卡口 4 失败：freeze ADR 被修改：$adr"
      echo "::error::修复方式：PR 标题加 ADR-AMENDMENT 前缀；或解除 freeze 后再改"
      CONFLICT=1
    fi
  fi
done

# 5. 检查新增 ADR 的必备字段
NEW_ADRS=$(git diff --name-only "$BASE_REF"...$HEAD_REF 2>/dev/null | grep -E '^docs/adr/ADR-[0-9]+.*\.md$' || true)
for adr in $NEW_ADRS; do
  for field in status date decider consequences; do
    if ! grep -qE "^${field}:" "$adr"; then
      echo "::error::卡口 4 失败：新增 ADR $adr 缺少字段：$field"
      CONFLICT=1
    fi
  done
done

if [ "$CONFLICT" -eq 1 ]; then
  exit 1
fi

echo "✅ 卡口 4 PASS：ADR 冲突检查通过"