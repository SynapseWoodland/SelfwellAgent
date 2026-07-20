---
phase: ATDD
run_id: "<run_id>"
role: qa-engineer
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null

# ATDD 专用字段
tds_ref: docs/architecture/TDS/TDS-M14-compliance.md   # 关联的 TDS（多对一）
atdd_docs:
  - path: harness/atdd/ATDD-S4-FR-M1-03.md          # 已有 ATDD
    action: reference                                     # reference=引用已有, create=新建, update=更新
  - path: harness/atdd/ATDD-S5-FR-M2-05.md            # 新建 ATDD
    action: create
---

# ATDD Phase Summary

## 文档来源

| 文档类型 | 路径 | 状态 |
|---------|------|------|
| TDS | `docs/architecture/TDS/TDS-M14-compliance.md` | 已关联 |
| ATDD | `harness/atdd/ATDD-*.md` | 按需新增 |

## 本轮 ATDD 变更

### 新增 ATDD

| ATDD 路径 | 关联 FR | 关联 TDS | 状态 |
|----------|---------|---------|------|
| - | - | - | - |

### 引用已有 ATDD

| ATDD 路径 | 关联 FR | 本轮用途 |
|----------|---------|---------|

## ATDD ↔ TDS 映射表

| TDS 模块 | ATDD 数量 | 最新 ATDD |
|---------|----------|---------|

## ATDD 变更检测流程

```
1. 进入 ATDD Phase 时
2. 确定目标 TDS（如 M14）
3. 确定目标 FR（如 FR-M2-05）
4. 检查对应 ATDD 是否存在
5.
   ├─► 存在 → 复用已有 ATDD，action: reference
   └─► 不存在 → 创建新 ATDD，action: create
6. 记录到 atdd_docs 列表
```

---

> **从0到1场景**：`created_from_scratch: true`，在下方记录创建了哪些 ATDD 文档。

## ATDD 章节模板

```markdown
# ATDD-<SprintID>-FR-<FR-ID>

## 基本信息
- **ATDD ID**: ATDD-S5-FR-M2-05
- **Sprint**: S5
- **关联 FR**: FR-M2-05
- **关联 TDS**: TDS-M14-compliance
- **创建日期**: 2026-07-20
- **最后更新**: 2026-07-20

## 验收标准

### AC-1: [验收项名称]
**Given** [前置条件]
**When** [操作]
**Then** [预期结果]

### AC-2: [验收项名称]
...

## 测试数据

| 测试用例 | 输入 | 预期输出 |
|---------|------|---------|
| TC-01 | ... | ... |

## 变更历史

| 日期 | Sprint | 变更内容 |
|-----|-------|---------|
| 2026-07-20 | S5 | 初始创建 |
```
