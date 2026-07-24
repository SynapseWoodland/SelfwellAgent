# Review Evidence 模板

此目录包含 V3 新增的所有 Review 节点的 evidence 模板。

## 命名规范

格式：`review-<phase-suffix>.md`

| 文件名 | 对应 Review 节点 | 审查深度 | 负责角色 |
|--------|-----------------|----------|----------|
| `review-srs.md` | REVIEW_SRS | medium | requirement-analyst |
| `review-arch.md` | REVIEW_ARCH | **heavy** | tech-architect |
| `review-atdd.md` | REVIEW_ATDD | light | quality-guardian |
| `review-tds.md` | REVIEW_TDS | medium | tech-architect |
| `review-plan.md` | REVIEW_PLAN | light | plan-generator |

## 审查深度说明

| 深度 | 说明 | 适用场景 |
|------|------|----------|
| **light** | 场景格式、Given-When-Then、覆盖度 | REVIEW_ATDD, REVIEW_PLAN |
| **medium** | 加上唯一真源检查、业务/技术对齐 | REVIEW_SRS, REVIEW_TDS |
| **heavy** | 加上架构方案选择、与用户澄清 | REVIEW_ARCH |

## 使用说明

1. 每次进入 Review 节点时，从对应模板复制到 `runs/<run_id>/` 目录
2. 填充模板内容
3. 在 `harness/state/harness-state.json` 中记录 evidence 路径

## Frontmatter 关键字段

```yaml
---
phase: REVIEW_XXX          # Review 节点 ID
review_depth: light        # light | medium | heavy
reviews_document: XXX      # 审查的文档类型
alignment_check: null      # PASS | WARN | FAIL | ARCH_CLARIFICATION
rejection_count: 0       # 打回次数，≥3 触发 ARCH_CLARIFICATION
---
```
