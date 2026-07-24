# Phase Evidence: VERIFY

> **模板版本**: V3.0
> **Phase**: VERIFY
> **负责角色**: verifier

---

## Frontmatter

```yaml
---
phase: VERIFY
run_id: "<uuid>"
role: verifier
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
---
```

---

## 一、验证结果

### 1.1 L0-L3 验证

| 门禁 | 命令 | 结果 |
|------|------|------|
| L0 | `python -m py_compile` | PASS/FAIL |
| L1 | `ruff check --fix && ruff format --check` | PASS/FAIL |
| L2 | `mypy --strict` | PASS/FAIL |
| L3 | `pytest tests/unit -x -q` | PASS/FAIL |

### 1.2 集成测试

| 测试项 | 结果 |
|--------|------|
| `<测试>` | PASS/FAIL |

---

## 二、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 DEPLOY 节点
