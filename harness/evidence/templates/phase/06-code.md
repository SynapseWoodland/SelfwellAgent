# Phase Evidence: CODE

> **模板版本**: V3.0
> **Phase**: CODE
> **负责角色**: developer

---

## Frontmatter

```yaml
---
phase: CODE
run_id: "<uuid>"
role: developer
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
tds_refs: []                         # 关联的 TDS
atdd_refs: []                        # 关联的 ATDD
---
```

---

## 一、实现概要

| 项目 | 内容 |
|------|------|
| Phase | `CODE` |
| 负责角色 | developer |
| 实现范围 | `<范围>` |

---

## 二、代码变更

### 2.1 新增文件

| 文件路径 | 描述 | 行数 |
|----------|------|------|
| `<path>` | `<描述>` | `<行数>` |

### 2.2 修改文件

| 文件路径 | 描述 | 变更类型 |
|----------|------|----------|
| `<path>` | `<描述>` | `<修改/重构>` |

---

## 三、质量门禁执行结果

| 门禁 | 结果 | 详情 |
|------|------|------|
| L0 | PASS/FAIL | `<详情>` |
| L1 | PASS/FAIL | `<详情>` |
| L2 | PASS/FAIL | `<详情>` |
| L3 | PASS/FAIL | `<详情>` |
| L4 | PASS/FAIL | `<详情>` |
| L6 | PASS/FAIL | `<覆盖率>` |

---

## 四、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 VERIFY 节点
