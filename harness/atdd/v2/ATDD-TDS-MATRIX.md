# ATDD-TDS 需求追踪矩阵

> **版本**: V1.0
> **日期**: 2026-07-22
> **状态**: Draft
> **用途**: 建立 ATDD（验收标准）与 TDS（技术设计）之间的双向追踪关系，实现需求到技术实现的可追溯性

---

## 一、矩阵说明

### 1.1 关联类型定义

| 符号 | 含义 | 说明 |
|------|------|------|
| `●` | 强关联（Primary） | 该 ATDD 的核心依赖，技术设计直接影响验收标准 |
| `○` | 弱关联（Secondary） | 该 ATDD 的支撑依赖，提供技术细节但不直接决定验收 |
| `△` | 横向依赖 | 跨域共享技术（如合规、时区、Persona） |

### 1.2 为什么是 N:M 关系

```
TDS（技术设计）角度：
┌─────────────────────────────────────────────────────────────┐
│ TDS-M5-persona-chat.md                                     │
│  - Persona 4 态状态机                                        │
│  - Intent/Topic 分类                                        │
│  - ACK 话术池                                              │
│                    ↓ 被以下 ATDD 引用                        │
│  ├── ATDD-Conversation.md (M5)        ← ● Primary          │
│  ├── ATDD-Feedback.md (M7)           ← ○ Secondary        │
│  ├── ATDD-Recall.md (M8) [J1-J4]  │ ← ○ Secondary        │
│  └── ATDD-Journey.md (跨域)           ← △ 横向依赖         │
└─────────────────────────────────────────────────────────────┘

ATDD（验收标准）角度：
┌─────────────────────────────────────────────────────────────┐
│ ATDD-Conversation.md (M5)                                   │
│  - 意图分类验收                                              │
│  - 对话流程验收                                              │
│                    ↓ 依赖以下 TDS                           │
│  ├── TDS-M5-persona-chat.md        ← ● Primary             │
│  ├── TDS-M14-compliance.md         ← ○ Secondary (合规)    │
│  ├── TDS-M12-timezone-cst-display.md ← △ 横向依赖         │
│  └── TDS-M1-wechat-login.md       ← △ 横向依赖 (用户)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、双向追踪矩阵

### 2.1 ATDD → TDS（验收标准依赖哪些技术设计）

| ATDD 文档 | 模块 | Primary TDS | Secondary TDS | 横向依赖 TDS |
|-----------|------|-------------|---------------|-------------|
| ATDD-Auth.md | M1 | `TDS-M1-wechat-login.md` | — | — |
| ATDD-Diagnosis.md | M2 | `TDS-M2-multimodal-diagnosis.md` | — | `TDS-M14-compliance.md`<br>**M2→M3 手动触发** |
| ATDD-Plan.md | M3 | `TDS-M3-21day-plan.md` | — | — |
| ATDD-Checkin.md | M4 | `TDS-M4-checkin-loop.md` | — | — |
| ATDD-Conversation.md | M5 | `TDS-M5-persona-chat.md` | `TDS-M14-compliance.md` | `TDS-M12-timezone-cst-display.md` |
| ATDD-Feedback.md | M7 | `TDS-M7-feedback.md`<br>`TDS-M7-time-album.md` | — | `TDS-M5-persona-chat.md` |
| ATDD-Recall.md | M8 | `TDS-M8-recall.md` | — | `TDS-M5-persona-chat.md`<br>`TDS-M14-compliance.md`<br>**J1-J4 逐条约束** |
| ATDD-Community.md | M6 | `TDS-M6-plaza-community.md` | — | `TDS-M14-compliance.md` |
| ATDD-Share.md | M10 | `TDS-M10-share-card.md` | — | — |
| ATDD-Push.md | M13 | `TDS-M13-push-scheduler.md` | — | `TDS-M12-timezone-cst-display.md` |
| ATDD-Compliance.md | M14 | `TDS-M14-compliance.md` | — | — |
| ATDD-Timezone.md | M12 | `TDS-M12-timezone-cst-display.md` | — | — |
| ATDD-Shared.md | 跨域 | — | — | `TDS-M5-persona-chat.md` (Persona) |
| ATDD-Journey.md | 跨域 | — | — | `TDS-M5-persona-chat.md` (对话状态) |
| ATDD-Contract-Fix.md | PRC | `TDS-M2-pr7-integration.md` | — | — |

### 2.2 TDS → ATDD（技术设计支撑哪些验收标准）

| TDS 文档 | Primary ATDD | Secondary ATDD | 横向依赖 ATDD |
|-----------|-------------|-----------------|--------------|
| `TDS-M1-wechat-login.md` | ATDD-Auth.md (M1) | — | ATDD-Conversation.md (M5) |
| `TDS-M2-multimodal-diagnosis.md` | ATDD-Diagnosis.md (M2) | — | — |
| `TDS-M3-21day-plan.md` | ATDD-Plan.md (M3) | — | — |
| `TDS-M4-checkin-loop.md` | ATDD-Checkin.md (M4) | — | — |
| `TDS-M5-persona-chat.md` | ATDD-Conversation.md (M5) | ATDD-Feedback.md (M7)<br>ATDD-Recall.md (M8) | ATDD-Shared.md<br>ATDD-Journey.md |
| `TDS-M6-plaza-community.md` | ATDD-Community.md (M6) | — | — |
| `TDS-M7-feedback.md` | ATDD-Feedback.md (M7) | — | — |
| `TDS-M7-time-album.md` | ATDD-Feedback.md (M7) | — | — |
| `TDS-M8-recall.md` | ATDD-Recall.md (M8) | — | — |
| `TDS-M10-share-card.md` | ATDD-Share.md (M10) | — | — |
| `TDS-M12-timezone-cst-display.md` | ATDD-Timezone.md (M12) | — | ATDD-Push.md (M13)<br>ATDD-Conversation.md (M5) |
| `TDS-M13-push-scheduler.md` | ATDD-Push.md (M13) | — | — |
| `TDS-M14-compliance.md` | ATDD-Compliance.md (M14) | ATDD-Diagnosis.md (M2)<br>ATDD-Conversation.md (M5)<br>ATDD-Recall.md (M8)<br>ATDD-Community.md (M6) | — |
| `TDS-M2-pr7-integration.md` | ATDD-Contract-Fix.md | — | — |

---

## 三、核心共享技术依赖图

### 3.1 横向依赖矩阵（Cross-cutting Concerns）

以下技术被多个模块共同依赖，需要特别注意变更影响：

```
                    ┌─────────────────────────────────────────────────────────┐
                    │              合规层（TDS-M14-compliance.md）             │
                    │  L1 输入拦截 / L2 LLM 约束 / L3 输出审查 / L4 异步复审   │
                    └──────────┬──────────┬──────────┬──────────┬──────────────┘
                               │          │          │          │
         ┌─────────────────────┼──────────┼──────────┼──────────┼────────────────┐
         │                     │          │          │          │                │
         ▼                     ▼          ▼          ▼          ▼                │
┌─────────────────┐    ┌────────────┐ ┌────────┐ ┌────────┐ ┌────────────┐    │
│ ATDD-Diagnosis │    │ ATDD-Conv  │ │ ATDD- │ │ ATDD- │ │ ATDD-      │    │
│ (M2)            │    │ (M5)       │ │ Recall │ │ Comm-  │ │ Compliance  │    │
│                 │    │            │ │ (M8)   │ │ unity  │ │ (M14)       │    │
└─────────────────┘    └────────────┘ └────────┘ └────────┘ └────────────┘    │
                                                                                │
                    ┌─────────────────────────────────────────────────────────┐
                    │           Persona 状态机（TDS-M5-persona-chat.md）       │
                    │     warm / neutral / slight_hug / medical_guarded        │
                    └──────────┬──────────────────┬───────────────────────────┘
                               │                  │
         ┌─────────────────────┼──────────────────┼────────────────────────────┐
         │                     │                  │                            │
         ▼                     ▼                  ▼                            │
┌─────────────────┐    ┌────────────┐    ┌────────────┐                     │
│ ATDD-Feedback   │    │ ATDD-Conv  │    │ ATDD-Recall│                     │
│ (M7)             │    │ (M5)       │    │ (M8)        │                     │
└─────────────────┘    └────────────┘    └────────────┘                     │
                                                                                │
                    ┌─────────────────────────────────────────────────────────┐
                    │          时区统一（TDS-M12-timezone-cst-display.md）      │
                    │            UTC 存储 · Asia/Shanghai 显示                  │
                    └──────────┬──────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼────────────────────────────────────────────┐
         │                     │                                              │
         ▼                     ▼                                              │
┌─────────────────┐    ┌────────────┐                                        │
│ ATDD-Push       │    │ ATDD-Conv  │                                        │
│ (M13)            │    │ (M5)       │                                        │
└─────────────────┘    └────────────┘                                        │
```

### 3.2 跨域共享技术清单

| 共享技术 | TDS 文档 | 被引用次数 | 影响 ATDD |
|---------|---------|-----------|---------|
| 合规四层纵深 | `TDS-M14-compliance.md` | 5 | M2, M5, M6, M8, M14 |
| Persona 状态机 | `TDS-M5-persona-chat.md` | 4 | M5, M7, M8, 跨域 |
| 时区统一 | `TDS-M12-timezone-cst-display.md` | 2 | M5, M13 |
| 用户认证 | `TDS-M1-wechat-login.md` | 1 | M5 |

---

## 四、变更影响评估指南

### 4.1 修改 TDS 时的评估流程

```
当修改 TDS-M14-compliance.md 时：
                    ↓
         ┌──────────────────┐
         │ 评估变更范围      │
         └────────┬─────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌───────┐   ┌──────────┐  ┌──────────┐
│ L1 变更 │   │ L2 变更  │  │ L4 变更  │
└───┬───┘   └────┬─────┘  └────┬─────┘
    │             │             │
    └─────────────┼─────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 影响 ATDD：                         │
│  • ATDD-Diagnosis (M2)   ○         │
│  • ATDD-Conversation (M5) ○        │
│  • ATDD-Recall (M8) [J1-J4]      ○        │
│  • ATDD-Community (M6)    ○         │
│  • ATDD-Compliance (M14)  ●         │
│                                     │
│ 需要同步更新：                       │
│  ✓ ATDD-Compliance.md 的相关 Scenario│
│  ✓ 通知其他模块负责人进行回归测试     │
└─────────────────────────────────────┘
```

### 4.2 新增 ATDD 时的评估流程

```
当新增 ATDD-NewFeature.md 时：
                    ↓
         ┌──────────────────┐
         │ 识别技术依赖      │
         └────────┬─────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌───────┐   ┌──────────┐  ┌──────────┐
│ 需要   │   │ 需要     │  │ 需要     │
│ Persona│   │ 合规审查 │  │ 时区处理 │
└───┬───┘   └────┬─────┘  └────┬─────┘
    │             │             │
    └─────┬───────┴──────┬──────┘
          │              │
          ▼              ▼
┌─────────────────┐  ┌─────────────────┐
│ 引用 TDS-M5     │  │ 引用 TDS-M14    │
│ (Persona)       │  │ (合规)          │
└─────────────────┘  └─────────────────┘
```

---

## 五、文档版本对应表

### 5.1 ATDD 版本 → TDS 版本对照

| ATDD 版本 | 日期 | TDS 版本要求 | 备注 |
|-----------|------|-------------|------|
| V1.0 | 2026-07-21 | — | 初始版本 |
| V1.1 | 2026-07-22 | — | 新增 TDS 关联列 |
| ... | ... | ... | ... |

### 5.2 修订历史

| 日期 | 版本 | 改动 | 作者 |
|------|------|------|------|
| 2026-07-22 | V1.0 | 初次创建矩阵文档 | SelfwellAgent |
| 2026-07-22 | V1.1 | 新增横向依赖图、变更影响评估指南 | SelfwellAgent |

---

## 六、附录

### 6.1 矩阵格式说明

本文档采用 **需求追踪矩阵（Requirement Traceability Matrix, RTM）** 格式：

| 字段 | 说明 |
|------|------|
| Primary | 核心依赖，变更直接影响验收 |
| Secondary | 支撑依赖，提供技术细节 |
| 横向依赖 | 跨域共享技术，影响多个模块 |

### 6.2 工具支持

未来可考虑使用以下工具自动化追踪：

- **Polarized**: 开源需求追踪工具
- **Jira + Confluence**: 原生追踪
- **Neo4j**: 图数据库可视化 N:M 关系

### 6.3 参考资料

- ATDD V2 索引：`harness/atdd/v2/README.md`
- TDS 索引：`docs/architecture/TDS/` 目录
- SRS 文档：`docs/requirements/SELFWELL-MVP-SRS.md`
