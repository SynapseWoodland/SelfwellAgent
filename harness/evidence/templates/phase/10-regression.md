# Phase Evidence: REGRESSION

> **模板版本**: V3.0
> **Phase**: REGRESSION
> **负责角色**: tester

---

## Frontmatter

```yaml
---
phase: REGRESSION
run_id: "<uuid>"
role: tester
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
---
```

---

## 一、回归测试结果

| 测试集 | 用例数 | 通过 | 失败 | 跳过 |
|--------|--------|------|------|------|
| `<测试集>` | `<数>` | `<数>` | `<数>` | `<数>` |

---

## 二、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 SIGN_OFF 节点
