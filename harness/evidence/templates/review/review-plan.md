# Review Evidence: PLAN 实施计划审查

> **模板版本**: V3.0
> **Review 节点**: REVIEW_PLAN
> **负责角色**: plan-generator
> **审查深度**: light

---

## Frontmatter

```yaml
---
phase: REVIEW_PLAN
run_id: "<uuid>"
role: plan-generator
fr_refs: []
adr_refs: []
signed: false
review_depth: "light"
reviews_document: "PLAN"
alignment_check: null
rejection_reason: null
rejection_count: 0
review_checkpoints:
  实施可行性检查: null
  依赖关系检查: null
  ddd规范检查: null
---
```

---

## 一、审查概要

| 项目 | 内容 |
|------|------|
| Review 节点 | `REVIEW_PLAN` |
| 审查文档 | 实施计划文档 |
| 审查深度 | **轻量**（light） |
| 负责角色 | plan-generator |
| 审查时间 | `<datetime>` |

---

## 二、轻量级检查

### 2.1 实施可行性检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 任务分解粒度 | PASS / WARN / FAIL | 任务是否分解到可执行粒度 |
| 时间估算合理性 | PASS / WARN / FAIL | 时间估算是否合理 |
| 验收标准明确 | PASS / WARN / FAIL | 每个任务是否有明确验收标准 |

### 2.2 依赖关系检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 依赖关系清晰 | PASS / WARN / FAIL | 任务依赖是否明确 |
| 依赖无循环 | PASS / WARN / FAIL | 依赖图是否无循环 |
| 关键路径识别 | PASS / WARN / FAIL | 是否识别了关键路径 |

### 2.3 DDD 规范检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Context 边界清晰 | PASS / WARN / FAIL | Context 边界是否符合设计 |
| Aggregate 完整性 | PASS / WARN / FAIL | Aggregate 是否完整 |
| Domain Event 定义 | PASS / WARN / FAIL | 是否正确定义了 Domain Event |

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
signed_by: plan-generator
signed_at: <datetime>
```
