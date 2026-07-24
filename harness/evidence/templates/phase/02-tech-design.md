# Phase Evidence: ARCH_DESIGN

> **模板版本**: V3.0
> **Phase**: ARCH_DESIGN
> **负责角色**: tech-architect

---

## Frontmatter

```yaml
---
phase: ARCH_DESIGN
run_id: "<uuid>"
role: tech-architect
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
source_sds: null                    # 已有 SDS 路径
source_tds_modules: []              # 本轮涉及的已有 TDS 模块
created_tds_modules: []             # 本轮新建的 TDS 模块
new_adrs: []                        # 本轮新增的 ADR
involved_architecture: []           # 架构文档变更
involved_data: []                   # data/*.yaml 变更
arch_change_type: null               # CORE_CHANGE | SIGNIFICANT_REF_CHANGE | MINOR_REF_CHANGE | null
requires_user_clarification: false
---
```

---

## 一、文档来源

| 文档类型 | 路径 | 状态 |
|---------|------|------|
| 架构设计 | `<path>` | `<已有/新建>` |
| ADR | `<path>` | `<已有/新建>` |

---

## 二、本轮涉及模块

| 模块 ID | 模块名称 | SDS 章节 | 变更类型 |
|--------|---------|---------|---------|
| `<模块ID>` | `<名称>` | `<章节>` | `<已有/变更/新建>` |

---

## 三、架构决策（ADR）

### 新增 ADR

| ADR ID | 标题 | 决策内容 |
|-------|------|---------|
| `<ADR-XXXX>` | `<标题>` | `<内容>` |

### 引用已有 ADR

| ADR ID | 本轮用途 |
|--------|---------|
| `<ADR-XXXX>` | `<用途>` |

---

## 四、技术设计变更

### 已有模块变更

| 模块 ID | 变更内容 | 影响范围 |
|--------|---------|---------|
| `<模块ID>` | `<变更>` | `<范围>` |

### 新增模块

| 模块 ID | 模块名称 | TDS 路径 |
|--------|---------|---------|
| `<模块ID>` | `<名称>` | `<路径>` |

---

## 五、架构变更评估

| 变更类型 | 是否涉及 | 说明 |
|----------|----------|------|
| 核心架构变更 | YES / NO | `<说明>` |
| 服务/模块结构变化 | YES / NO | `<说明>` |
| 接口契约变化 | YES / NO | `<说明>` |
| 数据模型变化 | YES / NO | `<说明>` |

---

## 六、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 REVIEW_ARCH 节点
