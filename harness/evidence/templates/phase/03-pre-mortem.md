# Phase Evidence: PRE_MORTEM

> **模板版本**: V3.0
> **Phase**: PRE_MORTEM
> **负责角色**: orchestrator

---

## Frontmatter

```yaml
---
phase: PRE_MORTEM
run_id: "<uuid>"
role: orchestrator
fr_refs: []
adr_refs: []
signed: true
interrupt_budget: 5
replay_session_id: null
---
```

---

## 一、风险评估

### 1.1 高风险项

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| `<风险1>` | 高/中/低 | 高/中/低 | `<措施>` |

### 1.2 中风险项

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| `<风险1>` | 高/中/低 | 高/中/低 | `<措施>` |

---

## 二、风险矩阵

```
         影响
概率     高      中      低
高      🔴      🟡      🟢
中      🟡      🟡      🟢
低      🟢      🟢      🟢
```

---

## 三、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 CODE 节点
