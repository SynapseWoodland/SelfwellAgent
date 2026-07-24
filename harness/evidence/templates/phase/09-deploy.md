# Phase Evidence: DEPLOY

> **模板版本**: V3.0
> **Phase**: DEPLOY
> **负责角色**: deployer

---

## Frontmatter

```yaml
---
phase: DEPLOY
run_id: "<uuid>"
role: deployer
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
---
```

---

## 一、部署结果

| 环境 | 状态 | 部署时间 | 部署人 |
|------|------|----------|--------|
| `<环境>` | `<成功/失败>` | `<时间>` | `<deployer>` |

---

## 二、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 REGRESSION 节点
