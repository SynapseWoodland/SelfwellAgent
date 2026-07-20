---
phase: ARCH_DESIGN
run_id: "<run_id>"
role: tech-architect
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null

# 文档来源字段
source_sds: docs/architecture/SELFWELL-MVP-SDS.md   # 已有 SDS 路径
source_tds_modules: []                              # 本轮涉及的已有 TDS 模块
created_tds_modules: []                             # 本轮新建的 TDS 模块
new_adrs: []                                       # 本轮新增的 ADR

# 架构文档来源（docs/architecture/ 下所有类型）
involved_architecture:
  - path: docs/architecture/api.yaml              # API 契约
    action: reference                            # create / update / reference
  - path: docs/architecture/error-codes.md       # 错误码
    action: reference
  - path: docs/architecture/sse-events.md         # SSE 事件
    action: reference

involved_data: []                                  # data/*.yaml 变更
---

# ARCH_DESIGN Phase Summary

## 文档来源

| 文档类型 | 路径 | 状态 |
|---------|------|------|
| 系统架构说明书 | `docs/architecture/SELFWELL-MVP-SDS.md` | 已有 |
| 模块设计 | `docs/architecture/TDS/TDS-M*.md` | 部分已有 |
| ADR | `docs/architecture/adr/ADR-*.md` | 已有 |

## 本轮涉及模块

| 模块 ID | 模块名称 | SDS 章节 | 变更类型 |
|--------|---------|---------|---------|
| M1 | 微信登录 | §2.1 | 已有 |

## 架构决策（ADR）

### 新增 ADR

| ADR ID | 标题 | 决策内容 |
|-------|------|---------|
| - | - | - |

### 引用已有 ADR

| ADR ID | 本轮用途 |
|-------|---------|

## 技术设计变更

### 已有模块变更

| 模块 ID | 变更内容 | 影响范围 |
|--------|---------|---------|

### 新增模块

| 模块 ID | 模块名称 | TDS 路径 |
|--------|---------|---------|

## 变更追踪

### 架构文档变更

| 文档类型 | 路径 | action | 变更说明 |
|---------|------|--------|---------|

### data/*.yaml 变更

| 文件 | 变更内容 |
|-----|---------|

---

> **从0到1场景**：`created_from_scratch: true`，在下方记录创建了哪些架构文档。
