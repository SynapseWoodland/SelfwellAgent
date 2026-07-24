# Phase Evidence: PLAN

> **模板版本**: V3.0
> **Phase**: PLAN
> **负责角色**: plan-generator

---

## Frontmatter

```yaml
---
phase: PLAN
run_id: "<uuid>"
role: plan-generator
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
tds_refs: []                         # 关联的 TDS 文档
atdd_refs: []                        # 关联的 ATDD 文档
---
```

---

## 一、计划概要

| 项目 | 内容 |
|------|------|
| Phase | `PLAN` |
| 负责角色 | plan-generator |
| 对应 ATDD | `<ATDD 文档引用>` |
| 对应 TDS | `<TDS 文档引用>` |

---

## 二、实施计划

### 2.1 主要里程碑

| 里程碑 | 计划日期 | 对应任务 | 状态 |
|--------|----------|-----------|------|
| `<里程碑1>` | `<日期>` | `<任务>` | 计划中 |

### 2.2 关键任务清单

| 任务 | 负责 | 依赖 | 复杂度 |
|------|--------|------|--------|
| `<任务1>` | `<role>` | `<依赖>` | 低/中/高 |
| `<任务2>` | `<role>` | `<依赖>` | 低/中/高 |

---

## 三、代码规范要求

### 3.1 DDD 规范

| 规范 | 要求 |
|------|------|
| Context 边界 | `<要求>` |
| Aggregate 完整性 | `<要求>` |
| Domain Event 定义 | `<要求>` |

### 3.2 编码规范

| 规范 | 要求 |
|------|------|
| 目录结构 | `<要求>` |
| 命名规范 | `<要求>` |
| 测试覆盖率 | ≥ 80% |

---

## 四、测试策略

### 4.1 单元测试

| 模块 | 测试策略 | 覆盖率目标 |
|------|----------|------------|
| `<模块>` | `<策略>` | ≥ 80% |

### 4.2 集成测试

| 测试项 | 描述 | 依赖 |
|--------|------|------|
| `<测试>` | `<描述>` | `<依赖>` |

---

## 五、质量门禁

| 门禁 | 命令 |
|------|------|
| L0 | `python -m py_compile` |
| L1 | `uv run ruff check --fix && uv run ruff format --check` |
| L2 | `uv run mypy --strict` |
| L3 | `uv run pytest tests/unit -x -q` |

---

## 六、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 REVIEW_PLAN 节点
