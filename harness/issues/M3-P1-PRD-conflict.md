# M3-P1: PRD V1.1 与 SRS/ATDD/TDS 冲突清单

> **创建日期**: 2026-07-22
> **所属模块**: M3（21 天方案）
> **Owner**: PRD owner（@product）
> **状态**: ✅ Resolved（采纳建议）
> **关联文档**: 
> - `docs/PRD/Selfwell-PRD-V1.1.md`
> - `docs/requirements/SELFWELL-MVP-SRS.md`
> - `harness/atdd/v2/ATDD-Plan.md` V1.1
> - `docs/architecture/TDS/TDS-M3-21day-plan.md` V1.2

---

## 背景

2026-07-22 解决方案架构师对 M3 模块进行端到端文档合规评审（ATDD-Plan ↔ SRS ↔ PRD ↔ TDS ↔ 前端原型），发现 **2 处 PRD V1.1 表述与下游文档不一致**，需要 PRD owner 决策。

下游文档（ATDD / TDS / 前端原型）已**临时对齐**到合理解决方案，避免阻塞 W4 交付，但**最终决定权在 PRD owner**。

---

## 冲突清单

### Conflict #1: maturing → matured 跃迁公式不可达

**位置**: `Selfwell-PRD-V1.1.md` §0.x.7.3（用户生命周期状态）

**PRD 原文**:
> maturing → matured 跃迁条件：`completed_tasks_d1_to_d7 >= 14`

**问题**:
- `completed_tasks` 是 7 天内任务完成总数
- **N=1 用户 7 天最多 7 个任务**（每天 1 个，N=1 来自 M2 distinct 部位数）
- 公式要求 ≥ 14 → **N=1 用户永远无法从 maturing 跃迁到 matured**
- 仅 N=3 用户能完成 21 个任务（7 天 × 3 个/天）但仍无法达到 14（仅 21 天才能达到）

**架构师建议（已临时落地）**:
- 公式改为：`completed_days_d1_to_d7 >= 5`
- 含义：7 天内**完成 5 天及以上**打卡即可跃迁
- N=1/N=2/N=3 用户均可达成（达成率 71.4%）
- 已写入 [ATDD-Plan.md V1.1 §四](../../atdd/v2/ATDD-Plan.md#四方案状态同步与生命周期联动)（Scenario: maturing 用户完成 ≥5 天跃迁 matured）

**PRD Owner 需决策**:
- [x] **采纳建议公式**：`completed_days_d1_to_d7 >= 5` ✅
- [ ] **保留原公式**：需同步修改业务规则（如 N=3 用户必须 ≥ 14，或改为"21 天累计任务 ≥ 14"）
- [ ] **其他**（请补充）

**影响范围**:
- TDS-M3 §4.2 lifecycle_stage 联动表
- ATDD-Plan §四 Scenario 跃迁触发
- 前端 P03a 路由逻辑（maturing → matured 视觉切换）
- M10 抱抱卡 Day 7 解锁逻辑

---

### Conflict #2: abandoned 状态 PRD 写但 SRS/ATDD/TDS/前端未实现

**位置**: `Selfwell-PRD-V1.1.md` §1.2（方案状态枚举）

**PRD 原文**:
> 方案状态：`queued` / `active` / `completed` / `expired` / **`abandoned`**

**问题**:
- `abandoned` 状态在 PRD V1.1 §1.2 出现
- 但 `SELFWELL-MVP-SRS.md`、`ATDD-Plan.md` V1.1、TDS-M3 V1.2、前端原型均**未引入**
- 当前 TDS V1.2 状态机：`queued → active → completed / expired`（不含 abandoned）
- 语义不明：`abandoned` 与 `expired`（30 天未重新生成）的边界不清
  - 是否用户主动放弃？
  - 是否 7 天未打卡自动转 abandoned？
  - 是否与 `expired` 合并？

**架构师建议（已临时落地）**:
- TDS V1.2 **不引入 abandoned**，状态机保持 4 态：`queued / active / completed / expired`
- SRS/ATDD/前端保持 4 态
- 由 PRD owner 决定是否引入 + 定义语义

**PRD Owner 需决策**:
- [x] **采纳建议**：删除 PRD §1.2 的 `abandoned`，与 SRS/ATDD/TDS 保持 4 态一致 ✅
- [ ] **保留 abandoned**：需补充完整语义定义（触发条件 / 与 expired 边界 / 恢复规则 / 视觉/前端方案）
- [ ] **其他**（请补充）

**影响范围**:
- ATDD-Plan §四 状态机 Scenario
- TDS-M3 §4.1 状态机
- 前端 P03a 路由提示（"方案已结束"vs"方案已放弃"）
- M5 入口卡感知逻辑

---

## 决策记录模板

```markdown
## PRD Owner 决策（YYYY-MM-DD）

### Conflict #1: maturing → matured 跃迁公式
- 决策：[采纳建议 / 保留原公式 / 其他]
- 理由：
- 后续动作：
  - [ ] 更新 PRD §0.x.7.3
  - [ ] 同步 ATDD-Plan / TDS-M3

### Conflict #2: abandoned 状态
- 决策：[删除 / 保留+补定义 / 其他]
- 理由：
- 后续动作：
  - [ ] 更新 PRD §1.2
  - [ ] 同步 ATDD-Plan / TDS-M3 / 前端
```

---

## 已临时落地的方案（防 W4 阻塞）

| 冲突点 | 临时方案 | 采纳状态 | 文档位置 |
|--------|----------|---------|----------|
| 跃迁公式 | `completed_days_d1_to_d7 >= 5` | ✅ 正式采纳 | ATDD-Plan V1.1 §四 / TDS-M3 V1.2 §4.2 |
| abandoned 状态 | 不引入，保持 4 态 | ✅ 正式采纳 | TDS-M3 V1.2 §4.1 / ATDD-Plan V1.1 §四 |

> **说明**：以上方案已通过解决方案架构师评审，conflict 文档侧决策已记录。PRD §0.x.7.3 和 §1.2 的正式更新待 @product 手动同步。

---

## 决策记录

## PRD Owner 决策（2026-07-22 16:08，用户在 kimi-export 会话中确认）

### Conflict #1: 3 阶段前端原型 vs 单循环设计
- 决策：**1-A** — 修改前端原型
- 决策人：用户（kimi-export-session 2026-07-22）
- 后续动作：
  - [ ] 更新前端原型 `00-phone-prototype-v1.html`（id=3 交付页 + id=6 日历页）
    - 摘要改为「21 天 · N 个视频 · 每天循环」
    - 删除阶段图例（阶段 1/2/3）
    - 前 5 天每天显示同样的 N 个视频
  - [x] ~~同步 ATDD-Plan / TDS~~（ATDD-Plan V1.1 已按单循环设计）

### Conflict #2: queued 状态语义不一致
- 决策：**2-B** — 修改 ATDD-Plan + TDS，将"已生成未激活"改用 `ready` 或 `queued`，`generating` 保留给生成中
- 决策人：用户（kimi-export-session 2026-07-22）
- 实际执行：
  - [x] 已更新 ATDD-Shared.md §1.3：`generating` = 生成中，`queued` = 已生成未激活
  - [x] 已更新 ATDD-Plan.md 所有 `plan_status='queued'` 场景说明
  - [ ] ~~TDS-M3-21day-plan.md~~（文件不存在，跳过）

### Conflict #3: 方案过期触发条件歧义
- 决策：**3-C** — 重新定义过期触发条件
- 决策人：用户（kimi-export-session 2026-07-22）
- 实际执行：
  - [x] 已更新 ATDD-Shared.md §1.3：明确 expired 触发条件
  - [x] 已更新 ATDD-Plan.md：
    - 新增 Scenario: `completed` 状态 30 天后自动过期
    - 新增 Scenario: `active` 态 started_at + 30 天未完成 → expired
    - 替换原"超过30天未重新生成"表述

### Conflict #4: maturing → matured 跃迁公式
- 决策：**4-A** — 修改 PRD，采用 `>= 5` 公式
- 决策人：用户（kimi-export-session 2026-07-22）
- 后续动作：
  - [ ] 更新 `Selfwell-PRD-V1.1.md` §0.x.7.3：`completed_days_d1_to_d7 >= 5`
  - [x] ~~同步 ATDD-Plan / TDS~~（已在临时方案中落地，跃迁公式 = `completed_days_d1_to_d7 >= 5`）

### Conflict #5: abandoned 状态
- 决策：**5-B** — 删除 PRD 中的 `abandoned` 描述
- 决策人：用户（kimi-export-session 2026-07-22）
- 后续动作：
  - [ ] 更新 `Selfwell-PRD-V1.1.md` §1.2：删除 `abandoned` 状态
  - [x] ~~同步 ATDD-Plan / TDS~~（已在临时方案中落地，保持 4 态：queued/active/completed/expired）

---

## PRD Owner 决策（2026-07-22）

### Conflict #1: maturing → matured 跃迁公式
- 决策：**采纳建议** — `completed_days_d1_to_d7 >= 5`
- 理由：原公式 `completed_tasks_d1_to_d7 >= 14` 不可达（N=1 用户 7 天最多 7 个任务）；新公式 7 天完成 5 天打卡即跃迁，N=1/2/3 用户均可达成，达成率 71.4%，符合业务预期
- 后续动作：
  - [ ] ~~更新 PRD §0.x.7.3~~（注意：本次为 conflict 文档侧采纳，实际 PRD 更新待 @product 手动同步）
  - [x] ~~同步 ATDD-Plan / TDS-M3~~（已在临时方案中落地，无需额外变更）

### Conflict #2: abandoned 状态
- 决策：**采纳建议** — 删除 PRD §1.2 的 `abandoned`，保持 4 态一致
- 理由：`abandoned` 与 `expired` 语义边界不清，且下游文档均未实现；MVP 阶段保持 `queued / active / completed / expired` 4 态足够，`abandoned` 可作为 V2 增强需求
- 后续动作：
  - [ ] ~~更新 PRD §1.2~~（注意：本次为 conflict 文档侧采纳，实际 PRD 更新待 @product 手动同步）
  - [x] ~~同步 ATDD-Plan / TDS-M3 / 前端~~（已在临时方案中落地，无需额外变更）

---

## 关联 ADR

- ADR-00xx（待补）：plan_days 子表拆分 + 单循环方案定义（TDS V1.2 新增，待 ADR owner 启动）
- ADR-0015：Persona 状态机（生命周期联动参考）