# ATDD V2 文档索引

> **版本**: V1.2
> **状态**: Draft
> **说明**: ATDD 文档整合版，按能力域重组，消除重复定义
> **TDS 对应**: 详见 [ATDD-TDS-MATRIX.md](ATDD-TDS-MATRIX.md)（需求追踪矩阵）

---

## 文档结构

```
v2/
├── ATDD-TDS-MATRIX.md    # ★ 需求追踪矩阵（双向关联，含变更影响评估）
├── ATDD-Shared.md        # 跨域共享定义（唯一真源）
├── ATDD-Journey.md       # 用户旅程覆盖
├── ATDD-Auth.md          # 认证与用户管理（M1）
├── ATDD-Diagnosis.md     # 多模态诊断（M2）
├── ATDD-Plan.md          # 21天方案（M3）
├── ATDD-Checkin.md       # 每日打卡（M4）
├── ATDD-Conversation.md   # 智能管家对话（M5）
├── ATDD-Feedback.md      # 反馈系统（M7 + M7-Album）
├── ATDD-Recall.md        # 主动回忆（M8）
├── ATDD-Community.md     # 广场社区（M6）
├── ATDD-Share.md         # 分享卡（M10）
├── ATDD-Push.md          # 推送调度（M13）
├── ATDD-Compliance.md    # 合规（M14）
├── ATDD-Timezone.md      # 时区显示（M12）
└── ATDD-Contract-Fix.md  # PR契约修复（PRC）
```

---

## 核心变更

### 1. 新增 ATDD-Shared.md
- 用户状态枚举（用户生命周期/诊断/方案/打卡/会话）
- feedback 定义（唯一真源，解决M7/M5/M8定义不一致）
- 合规红线（唯一真源，解决M5/M6/M7/M8/M10/M14重复定义）
- 错误码字典（唯一真源）
- 降级策略（唯一真源）
- Persona 状态机（唯一真源）
- ACK 话术池规范（唯一真源）

### 2. 新增 ATDD-Journey.md
- 冷启动旅程（M1 + M5）
- 诊断旅程（M2 + M5）
- 方案旅程（M3 + M4 + M5）
- 反馈旅程（M7 + M5 + M8）
- 回忆旅程（M8 + M5 + M7）
- 方案结束后旅程（M3 + M4 + M5）
- 诊断过期旅程（M2 + M3 + M5）
- 错误恢复旅程
- 跨日/跨时区旅程

### 3. 文档合并
| 原文档 | 合并后 |
|--------|---------|
| M7 + M7-Album | ATDD-Feedback.md |

### 4. 修复的问题
- M5-FR-08 与 M5-FR-03 矛盾（"坚持7天"改为不提具体天数）
- 补充诊断状态同步场景（M2→M5）
- 补充方案状态同步场景（M3→M5）
- 补充打卡与feedback关联场景（M4→M5）

---

## TDS 关联表

| ATDD 文档 | 模块 | 对应 TDS 文档 |
|-----------|------|---------------|
| ATDD-Auth.md | M1 | `TDS-M1-wechat-login.md` |
| ATDD-Diagnosis.md | M2 | `TDS-M2-multimodal-diagnosis.md` |
| ATDD-Plan.md | M3 | `TDS-M3-21day-plan.md` |
| ATDD-Checkin.md | M4 | `TDS-M4-checkin-loop.md` |
| ATDD-Conversation.md | M5 | `TDS-M5-persona-chat.md` |
| ATDD-Feedback.md | M7 + M7-Album | `TDS-M7-feedback.md` + `TDS-M7-time-album.md` |
| ATDD-Recall.md | M8 | `TDS-M8-recall.md` |
| ATDD-Community.md | M6 | `TDS-M6-plaza-community.md` |
| ATDD-Share.md | M10 | `TDS-M10-share-card.md` |
| ATDD-Push.md | M13 | `TDS-M13-push-scheduler.md` |
| ATDD-Compliance.md | M14 | `TDS-M14-compliance.md` |
| ATDD-Timezone.md | M12 | `TDS-M12-timezone-cst-display.md` |
| ATDD-Shared.md | 跨域 | `TDS-M5-persona-chat.md`（Persona 状态机） |
| ATDD-Journey.md | 跨域 | `TDS-M5-persona-chat.md`（M5 对话状态） |

---

## 引用规范

所有模块文档必须引用 ATDD-Shared.md：

```markdown
### 相关定义
- 用户状态枚举：详见 [ATDD-Shared.md §一](../ATDD-Shared.md#一用户状态枚举)
- 合规红线：详见 [ATDD-Shared.md §三](../ATDD-Shared.md#三合规红线)
- 错误码定义：详见 [ATDD-Shared.md §四](../ATDD-Shared.md#四错误码字典)
```

---

## 修订历史

| 日期 | 版本 | 改动 | 来源 |
|------|------|------|------|
| 2026-07-22 | V1.2 | 新增 ATDD-TDS-MATRIX.md 需求追踪矩阵；README 引用矩阵文档 | 文档对齐 |
| 2026-07-22 | V1.1 | 新增 TDS 关联表，所有模块文档补充 TDS 引用 | 文档对齐 |
| 2026-07-21 | V1.0 | 初次创建整合版 | ATDD整合分析 |
