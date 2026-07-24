# Evidence: 架构澄清

> **模板版本**: V3.0
> **Phase**: ARCH_CLARIFICATION
> **触发条件**: Review 节点 3次打回后无法对齐
> **负责角色**: tech-architect

---

## Frontmatter

```yaml
---
phase: ARCH_CLARIFICATION
run_id: "<uuid>"
role: tech-architect
fr_refs: []
adr_refs: []
signed: false
clarification_type: null      # CORE_CHANGE | SIGNIFICANT_REF_CHANGE | MINOR_REF_CHANGE
triggering_review: null      # REVIEW_SRS | REVIEW_ARCH | REVIEW_ATDD | REVIEW_TDS | REVIEW_PLAN
rejection_count: 0
options_provided: []
user_approved: false
user_selected_option: null
resolution: null             # ACCEPTED | MODIFIED | REJECTED
---
```

---

## 一、澄清概要

| 项目 | 内容 |
|------|------|
| Phase | `ARCH_CLARIFICATION` |
| 触发 Review | `<REVIEW_XXX>` |
| 澄清类型 | `<CORE_CHANGE | SIGNIFICANT_REF_CHANGE | MINOR_REF_CHANGE>` |
| 负责角色 | tech-architect |
| 触发时间 | `<datetime>` |

---

## 二、问题详细说明

### 2.1 问题背景

```
<详细描述问题的背景、上下文>
```

### 2.2 影响范围

| 影响维度 | 具体影响 |
|----------|----------|
| 功能影响 | `<描述>` |
| 技术影响 | `<描述>` |
| 业务影响 | `<描述>` |

---

## 三、方案选项

### 方案 A

- **方案描述**: `<详细描述>`
- **优点**: `<列出优点>`
- **缺点**: `<列出缺点>`
- **时间估算**: `<时间>`

### 方案 B

- **方案描述**: `<详细描述>`
- **优点**: `<列出优点>`
- **缺点**: `<列出缺点>`
- **时间估算**: `<时间>`

---

## 四、建议

```
推荐选项: <A | B>
理由: <简要说明>
```

---

## 五、用户决策

```
用户选择的方案: <A | B | 其他>
用户说明: <用户提供的额外说明或修改要求>
resolution: <ACCEPTED | MODIFIED | REJECTED>
decided_at: <datetime>
```

---

## 六、后续行动

### 6.1 确认的修改

```
<确认的架构修改内容>
```

### 6.2 后续步骤

| 步骤 | 负责 | 状态 |
|------|--------|------|
| `<步骤1>` | `<role>` | 待执行 |
| `<步骤2>` | `<role>` | 待执行 |

---

## 七、审查签字

```
signed: <true | false>
signed_by: tech-architect
signed_at: <datetime>
```
