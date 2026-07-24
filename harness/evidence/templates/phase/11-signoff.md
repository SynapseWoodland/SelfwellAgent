# Phase Evidence: SIGN_OFF

> **模板版本**: V3.0
> **Phase**: SIGN_OFF
> **负责角色**: orchestrator

---

## Frontmatter

```yaml
---
phase: SIGN_OFF
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

## 一、签署确认

| 项目 | 状态 |
|------|------|
| 所有 phase 完成 | ✅/❌ |
| 质量门禁通过 | ✅/❌ |
| 测试通过 | ✅/❌ |
| 文档齐全 | ✅/❌ |

---

## 二、签署人

| 角色 | 签署人 | 日期 |
|------|--------|------|
| orchestrator | `<name>` | `<date>` |
