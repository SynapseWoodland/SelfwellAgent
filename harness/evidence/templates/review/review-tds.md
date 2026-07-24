# Review Evidence: TDS 文档审查

> **模板版本**: V3.0
> **Review 节点**: REVIEW_TDS
> **负责角色**: tech-architect
> **审查深度**: medium

---

## Frontmatter

```yaml
---
phase: REVIEW_TDS
run_id: "<uuid>"
role: tech-architect
fr_refs: []
adr_refs: []
signed: false
review_depth: "medium"
reviews_document: "TDS"
alignment_check: null
rejection_reason: null
rejection_count: 0
review_checkpoints:
  atdd_alignment: null       # PASS | WARN | FAIL
  技术可行性检查: null
  架构一致性检查: null
---
```

---

## 一、审查概要

| 项目 | 内容 |
|------|------|
| Review 节点 | `REVIEW_TDS` |
| 审查文档 | TDS 技术设计文档 |
| 审查深度 | **中等**（medium） |
| 负责角色 | tech-architect |
| 审查时间 | `<datetime>` |

---

## 二、对齐检查

### 2.1 ATDD 对齐检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| ATDD 场景覆盖 | PASS / WARN / FAIL | 每个 ATDD 场景是否有对应 TDS 实现 |
| 验收标准映射 | PASS / WARN / FAIL | ATDD 的 Given-When-Then 是否映射到 TDS 实现 |
| 测试策略对齐 | PASS / WARN / FAIL | TDS 中的测试策略是否满足 ATDD 覆盖要求 |

### 2.2 技术可行性检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 依赖可用性 | PASS / WARN / FAIL | 依赖的技术组件是否可用 |
| 复杂度评估 | PASS / WARN / FAIL | 实现复杂度是否合理 |
| 性能预估 | PASS / WARN / FAIL | 是否满足 NFR 目标 |

### 2.3 架构一致性检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 与架构设计对齐 | PASS / WARN / FAIL | TDS 是否符合 ARCH_DESIGN 的约束 |
| 模块边界清晰 | PASS / WARN / FAIL | 模块边界是否符合 DDD 规范 |
| 接口契约一致 | PASS / WARN / FAIL | API 契约是否与架构一致 |

---

## 三、TDS 模块清单

| 模块名称 | 对应 ATDD | 复杂度 | 状态 |
|----------|-----------|--------|------|
| `<模块1>` | `<ATDD场景>` | 低/中/高 | PASS / WARN / FAIL |

---

## 四、打回记录

### 4.1 打回历史

| 轮次 | 打回原因 | 修改内容 | 状态 |
|------|----------|----------|------|
| 1 | `<原因>` | `<修改>` | 已修改 |
| 2 | `<原因>` | `<修改>` | 已修改 |
| 3 | `<原因>` | - | **触发 ARCH_CLARIFICATION** |

---

## 五、审查签字

```
signed: <true | false>
signed_by: tech-architect
signed_at: <datetime>
```
