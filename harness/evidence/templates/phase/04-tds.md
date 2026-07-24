# Phase Evidence: TDS

> **模板版本**: V3.0
> **Phase**: TDS
> **负责角色**: tech-architect

---

## Frontmatter

```yaml
---
phase: TDS
run_id: "<uuid>"
role: tech-architect
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
tds_modules: []                        # TDS 模块列表
atdd_refs: []                          # 关联的 ATDD
arch_refs: []                          # 关联的架构文档
---
```

---

## 一、TDS 概要

| 项目 | 内容 |
|------|------|
| Phase | `TDS` |
| 负责角色 | tech-architect |
| 对应 ATDD | `<ATDD 文档引用>` |
| 对应架构 | `<ARCH_DESIGN 文档引用>` |

---

## 二、TDS 模块清单

| 模块名称 | 对应 ATDD 场景 | 对应架构模块 | 复杂度 |
|----------|----------------|--------------|--------|
| `<模块1>` | `<ATDD场景>` | `<架构模块>` | 低/中/高 |
| `<模块2>` | `<ATDD场景>` | `<架构模块>` | 低/中/高 |

---

## 三、模块详细设计

### 3.1 模块 1: `<模块名称>`

#### 3.1.1 模块概述

```
<模块的功能描述>
```

#### 3.1.2 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 编程语言 | `<语言>` | `<理由>` |
| 框架 | `<框架>` | `<理由>` |
| 数据库 | `<数据库>` | `<理由>` |

#### 3.1.3 接口设计

| 方法 | 路径 | 描述 | 请求 | 响应 |
|------|------|------|------|------|
| `<GET/POST>` | `/api/xxx` | `<描述>` | `<schema>` | `<schema>` |

#### 3.1.4 数据模型

```sql
CREATE TABLE `<table_name>` (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- 业务字段
  <field1> <type> <constraints>,
  deleted_at TIMESTAMPTZ NULL
);
```

#### 3.1.5 ATDD 场景映射

| ATDD 场景 | 对应实现 | 验证方式 |
|-----------|----------|----------|
| `<ATDD场景1>` | `<实现>` | `<验证>` |

---

## 四、技术约束

### 4.1 合规要求

| 要求 | 实现方式 |
|------|----------|
| 数据加密 | `<实现>` |
| 敏感信息保护 | `<实现>` |

### 4.2 性能要求

| 指标 | 目标 | 实现方式 |
|------|------|----------|
| 响应时间 P95 | `<目标>` | `<实现>` |

---

## 五、实施计划

### 5.1 任务分解

| 任务 | 负责 | 依赖 | 估算 |
|------|--------|------|------|
| `<任务1>` | `<role>` | `<依赖>` | `<估算>` |

### 5.2 里程碑

| 里程碑 | 目标日期 | 交付物 |
|--------|----------|--------|
| `<里程碑1>` | `<日期>` | `<交付物>` |

---

## 六、下一步

1. Dispatcher 校验 exit_criteria
2. 进入 REVIEW_TDS 节点
