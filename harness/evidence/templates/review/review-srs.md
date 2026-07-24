# Review Evidence: SRS 文档审查

> **模板版本**: V3.0
> **Review 节点**: REVIEW_SRS
> **负责角色**: requirement-analyst
> **审查深度**: medium

---

## Frontmatter

```yaml
---
phase: REVIEW_SRS
run_id: "<uuid>"
role: requirement-analyst
fr_refs: []
signed: false
review_depth: "medium"
reviews_document: "SRS"
alignment_check: null        # PASS | WARN | FAIL | ARCH_CLARIFICATION
rejection_reason: null
rejection_count: 0
source_doc_verified: false
review_checkpoints:
  唯一真源检查: null        # PASS | WARN | FAIL
  业务对齐检查: null         # PASS | WARN | FAIL
---
```

---

## 一、审查概要

| 项目 | 内容 |
|------|------|
| Review 节点 | `REVIEW_SRS` |
| 审查文档 | SRS 文档 |
| 审查深度 | **中等**（medium） |
| 负责角色 | requirement-analyst |
| 审查时间 | `<datetime>` |

---

## 二、对齐检查（三维度）

### 2.1 唯一真源检查

> 检查 SRS 文档是否为相关功能的唯一真源，是否存在多处定义冲突。

| 检查项 | 结果 | 说明 |
|--------|------|------|
| PRD 真源确认 | PASS / WARN / FAIL | PRD 文档是否明确引用 SRS |
| SRS 完整性 | PASS / WARN / FAIL | SRS 是否覆盖所有 FR |
| 多处定义冲突 | PASS / WARN / FAIL | 是否存在多处定义不一致 |

### 2.2 业务对齐检查

> 检查 SRS 是否与 PRD 的业务需求一致。

| 检查项 | 结果 | 说明 |
|--------|------|------|
| FR 编号覆盖 | PASS / WARN / FAIL | 所有 FR 是否有对应 SRS 章节 |
| 业务场景覆盖 | PASS / WARN / FAIL | 主要用户旅程是否完整 |
| 验收标准对齐 | PASS / WARN / FAIL | SRS 中的 AC 是否与 PRD 一致 |

### 2.3 整体对齐结论

```
alignment_check: <PASS | WARN | FAIL | ARCH_CLARIFICATION>

理由：<简要说明>
```

---

## 三、打回记录

### 3.1 打回历史

| 轮次 | 打回原因 | 修改内容 | 状态 |
|------|----------|----------|------|
| 1 | `<原因>` | `<修改>` | 已修改 |
| 2 | `<原因>` | `<修改>` | 已修改 |
| 3 | `<原因>` | - | **触发 ARCH_CLARIFICATION** |

---

## 四、审查签字

```
signed: <true | false>
signed_by: requirement-analyst
signed_at: <datetime>
```
