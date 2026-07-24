# Review Evidence: ATDD 文档审查

> **模板版本**: V3.0
> **Review 节点**: REVIEW_ATDD
> **负责角色**: quality-guardian
> **审查深度**: light

---

## Frontmatter

```yaml
---
phase: REVIEW_ATDD
run_id: "<uuid>"
role: quality-guardian
fr_refs: []
adr_refs: []
signed: false
review_depth: "light"
reviews_document: "ATDD"
alignment_check: null
rejection_reason: null
rejection_count: 0
review_checkpoints:
  scenario_format: null      # PASS | WARN | FAIL
  coverage_check: null       # PASS | WARN | FAIL
  gwt_syntax_check: null   # PASS | WARN | FAIL
---
```

---

## 一、审查概要

| 项目 | 内容 |
|------|------|
| Review 节点 | `REVIEW_ATDD` |
| 审查文档 | ATDD 文档 |
| 审查深度 | **轻量**（light） |
| 负责角色 | quality-guardian |
| 审查时间 | `<datetime>` |

---

## 二、轻量级检查

### 2.1 Given-When-Then 格式检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Feature 标题 | PASS / WARN / FAIL | 是否清晰描述功能 |
| Scenario 标题 | PASS / WARN / FAIL | 是否描述具体场景 |
| Given 语法 | PASS / WARN / FAIL | Given 是否正确描述前置条件 |
| When 语法 | PASS / WARN / FAIL | When 是否正确描述行为 |
| Then 语法 | PASS / WARN / FAIL | Then 是否正确描述预期结果 |

### 2.2 覆盖率检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 正常路径覆盖 | PASS / WARN / FAIL | Happy path 是否覆盖 |
| 边界条件覆盖 | PASS / WARN / FAIL | Edge case 是否覆盖 |
| FR 编号对齐 | PASS / WARN / FAIL | 场景是否关联对应 FR |

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
signed_by: quality-guardian
signed_at: <datetime>
```
