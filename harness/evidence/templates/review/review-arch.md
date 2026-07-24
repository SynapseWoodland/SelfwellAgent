# Review Evidence: 架构设计文档审查

> **模板版本**: V3.0
> **Review 节点**: REVIEW_ARCH
> **负责角色**: tech-architect
> **审查深度**: heavy

---

## Frontmatter

```yaml
---
phase: REVIEW_ARCH
run_id: "<uuid>"
role: tech-architect
fr_refs: []
adr_refs: []
signed: false
review_depth: "heavy"
reviews_document: "ARCH_DESIGN"
alignment_check: null
rejection_reason: null
rejection_count: 0
arch_change_type: null        # CORE_CHANGE | SIGNIFICANT_REF_CHANGE | MINOR_REF_CHANGE | null
requires_user_clarification: false
arch_clarification_approved: false
arch_options_provided: []
review_checkpoints:
  唯一真源检查: null
  技术对齐检查: null
  架构变更评估: null
---
```

---

## 一、审查概要

| 项目 | 内容 |
|------|------|
| Review 节点 | `REVIEW_ARCH` |
| 审查文档 | 架构设计文档 |
| 审查深度 | **重度**（heavy） |
| 负责角色 | tech-architect |
| 审查时间 | `<datetime>` |

### 1.2 架构变更类型

```
arch_change_type: <CORE_CHANGE | SIGNIFICANT_REF_CHANGE | MINOR_REF_CHANGE | null>
```

- **CORE_CHANGE**: 涉及核心架构决策变化，必须与用户澄清
- **SIGNIFICANT_REF_CHANGE**: 涉及引用文档重大变化，需要与用户确认
- **MINOR_REF_CHANGE**: 一般性文档更新，可直接审核
- **null**: 无架构变更

---

## 二、对齐检查

### 2.1 唯一真源检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 架构文档真源 | PASS / WARN / FAIL | tech-architecture-design-v3.md 是否为唯一真源 |
| ADR 一致性 | PASS / WARN / FAIL | ADR 决策是否与架构文档一致 |
| 引用文档完整性 | PASS / WARN / FAIL | 所有引用的文档是否存在 |

### 2.2 技术对齐检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 技术可行性 | PASS / WARN / FAIL | 架构方案是否技术上可行 |
| 依赖评估 | PASS / WARN / FAIL | 外部依赖是否合理 |
| 性能目标 | PASS / WARN / FAIL | 是否满足 NFR 目标 |
| 安全合规 | PASS / WARN / FAIL | 是否满足合规要求 |

### 2.3 架构变更评估

| 变更类型 | 是否涉及 | 说明 |
|----------|----------|------|
| 核心架构变更 | YES / NO | `<说明>` |
| 服务/模块结构变化 | YES / NO | `<说明>` |
| 接口契约变化 | YES / NO | `<说明>` |
| 数据模型变化 | YES / NO | `<说明>` |

---

## 三、架构方案选择（若涉及 CORE_CHANGE）

### 3.1 方案选项

#### 选项 A

- **方案描述**: `<描述>`
- **优点**: `<列出优点>`
- **缺点**: `<列出缺点>`
- **适用场景**: `<适用场景>`

#### 选项 B

- **方案描述**: `<描述>`
- **优点**: `<列出优点>`
- **缺点**: `<列出缺点>`
- **适用场景**: `<适用场景>`

### 3.2 建议

```
推荐选项: <A | B>
理由: <简要说明>
```

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
