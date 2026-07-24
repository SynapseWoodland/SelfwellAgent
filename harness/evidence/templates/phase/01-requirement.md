# Phase Evidence: REQUIREMENT

> **模板版本**: V3.0
> **Phase**: REQUIREMENT
> **负责角色**: requirement-analyst

---

## Frontmatter

```yaml
---
phase: REQUIREMENT
run_id: "<uuid>"
role: requirement-analyst
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
source_doc: null                    # 已有需求文档路径
created_from_scratch: false           # true=从0创建，false=引用已有
source_doc_sections: []              # 本轮涉及已有文档的章节
---
```

---

## 一、文档来源

| 文档类型 | 路径 | 状态 |
|---------|------|------|
| PRD | `<path>` | `<已有/新建>` |
| SRS | `<path>` | `<已有/新建>` |

---

## 二、FR 拆解

| FR ID | 名称 | 关联 ATDD | 关联 TDS |
|-------|------|----------|----------|
| `<FR-XXX>` | `<名称>` | `<ATDD路径>` | `<TDS路径>` |

---

## 三、关键 ADR 引用

| ADR ID | 本轮用途 |
|--------|----------|
| `<ADR-XXXX>` | `<用途>` |

---

## 四、决策请求

| # | 决策项 | 候选 | 推荐 |
|---|--------|------|------|
| 1 | `<决策项>` | (a) / (b) | `<推荐>` |

---

## 五、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 REVIEW_SRS 节点
