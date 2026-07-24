# Phase Evidence: ATDD

> **模板版本**: V3.0
> **Phase**: ATDD
> **负责角色**: quality-guardian

---

## Frontmatter

```yaml
---
phase: ATDD
run_id: "<uuid>"
role: quality-guardian
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
tds_ref: null                        # 关联的 TDS
atdd_docs: []                        # ATDD 文档列表
---
```

---

## 一、文档来源

| 文档类型 | 路径 | 状态 |
|---------|------|------|
| TDS | `<path>` | `<已有/新建>` |
| ATDD | `<path>` | `<已有/新建>` |

---

## 二、ATDD 变更

### 新增 ATDD

| ATDD 路径 | 关联 FR | 关联 TDS | 状态 |
|-----------|---------|---------|------|
| `<path>` | `<FR-ID>` | `<TDS-ID>` | `<新建>` |

### 引用已有 ATDD

| ATDD 路径 | 关联 FR | 本轮用途 |
|-----------|---------|---------|
| `<path>` | `<FR-ID>` | `<用途>` |

---

## 三、ATDD ↔ TDS 映射表

| TDS 模块 | ATDD 数量 | 最新 ATDD |
|---------|----------|---------|
| `<模块ID>` | `<数量>` | `<path>` |

---

## 四、ATDD 章节模板

```markdown
# ATDD-<SprintID>-FR-<FR-ID>

## 基本信息
- **ATDD ID**: ATDD-SX-FR-XXX
- **Sprint**: SX
- **关联 FR**: FR-XXX
- **关联 TDS**: TDS-XXX
- **创建日期**: <date>
- **最后更新**: <date>

## 验收标准

### AC-1: <验收项名称>
**Given** <前置条件>
**When** <操作>
**Then** <预期结果>

## 测试数据

| 测试用例 | 输入 | 预期输出 |
|---------|------|---------|
| TC-01 | ... | ... |

## 变更历史

| 日期 | Sprint | 变更内容 |
|-----|-------|---------|
| <date> | SX | 初始创建 |
```

---

## 五、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 REVIEW_ATDD 节点
