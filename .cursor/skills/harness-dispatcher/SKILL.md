---
name: harness-dispatcher
description: >
  Harness 调度入口 skill。当主会话说"进入 harness"/"按 Harness 跑"/"按流水线"/状态机 phase 切换时触发；
  读 harness/state/harness-state.json + harness/workflow-v2.yaml，返回 next_agent 指令。
  支持 interrupt/replay 路由：当 interrupt_budget > 0 时自动路由到 INTERRUPT_REVIEW；budget 耗尽后请求 AskUser。
  本 skill 只做路由——不调代码工具、不读 evidence、不写业务文件。详细协议见 agents/harness/DISPATCHER.md。
disable-model-invocation: false
---

# Harness Dispatcher（A 档精简版）

> 路由器 ≠ 执行器。每轮消息首句调它；只读 state + workflow，返回 next_agent。

## 一、触发条件

| 触发 | 场景 |
|------|------|
| 显式 | "进入 harness" / "按 Harness 跑" / "按流水线做" / "启动 harness" |
| 隐式 | "走流水线" / "按状态机" / "先 PRD 再 ARCH" |
| 阶段切换 | 当前 phase evidence 写完，询问"下一步" |
| orchestrator | 收到"请求下一 phase"事件 |
| 中断 | 用户追问 / 显式说"中断"/"暂停"/"interrupt"（且 `interruptible: true`） |
| 恢复 | 中断 review 完成后请求恢复执行 |

> **不触发**：让改一个 bug / 跑一个单测 / 看一段代码——属 `coding-standards` + `pr-gate`，不走 harness。

## 二、调用协议（6 步）

1. **Read** `harness/state/harness-state.json`（不存在则 `next_agent = orchestrator` 初始化）
2. **Read** `harness/workflow-v2.yaml`（V2 唯一真源，**不再读** `workflow.yaml`）
3. **中断检查**：若用户显式触发"中断/暂停/interrupt"，且当前 phase `interruptible: true`：
   - 读取当前 `interrupt_budget`
   - 若 `interrupt_budget <= 0`，返回 `next_agent = AskUser` 请求授权超限
   - 否则：`interrupt_budget - 1`，记录 `interrupted_phase`，`next_agent = quality-guardian`，context 指向 `harness/context/16-interrupt-review.md`
4. **DATA_REPLAY 特殊处理**：完成后 `next_phase_hint = "auto-cycle-to-PRD"`，`replay_session_id` 自增
5. **正常路由**：校验 `exit_criteria`，全满足 → `next[0]`；未满足 → 当前 phase `entry_agent`；SIGN_OFF 且 next=[] → `DONE`
6. 返回结构化指令：

| 字段 | 值 |
|------|---|
| run_id | `<uuid>` |
| current_phase | `<name>` |
| next_agent | `<role-name 或 DONE 或 AskUser>` |
| context_to_load | `harness/context/<phase-specific>.md`（V2 6 个新 phase 各有专属模板，见下） |
| evidence_required | `harness/evidence/<phase>.md` |

7. 调 `<next_agent>`（参考 `agents/harness/<FILE>.md`）；按需 Read 上述 context；evidence 落点由对应 agent 写

### V2 phase context 映射表

| phase | context 路径 |
|-------|-------------|
| PRD | `harness/context/phase-checklist.md` |
| ARCH_DESIGN | `harness/context/phase-checklist.md` |
| PRE_MORTEM | `harness/context/phase-checklist.md` |
| ATDD | `harness/context/phase-checklist.md` |
| PLAN | `harness/context/phase-checklist.md` |
| CODE | `harness/context/phase-checklist.md` |
| VERIFY | `harness/context/phase-checklist.md` |
| DEPLOY | `harness/context/phase-checklist.md` |
| REGRESSION | `harness/context/phase-checklist.md` |
| SIGN_OFF | `harness/context/phase-checklist.md` |
| SECURITY_TEST | `harness/context/11-security-test.md`（待 W12 P2 3.1.1 落地） |
| INCIDENT_RESPONSE | `harness/context/13-incident-response.md`（待 W12 P2 3.1.3 落地） |
| OPS_LOOP | `harness/context/14-ops-loop.md`（待 W12 P2 3.1.4 落地） |
| SKILL_UPDATE | `harness/context/15-skill-update.md`（待 W12 P2 3.1.5 落地） |
| DATA_REPLAY | `harness/context/12-data-replay.md`（待 W12 P2 3.1.2 落地） |
| INTERRUPT_REVIEW | `harness/context/16-interrupt-review.md`（待 W12 P2 3.1.6 落地） |

> **落地前**：6 个新 phase 的 context 路径暂时指向 `phase-checklist.md` 合一份；W12 P2 落地后逐个拆出独立模板。

## 三、严格禁止（红线）

| # | 禁止 | 兜底 |
|---|------|------|
| 1 | Read `evidence/*.md` | 主会话 ≤ 8K 上下文 |
| 2 | Read `atdd/*.md`（除 orchestrator 显式要求） | 同上 |
| 3 | Write `harness-state.json`（除初始化 run 外） | orchestrator 写权限独占 |
| 4 | 调业务代码工具（shell / pytest / git commit） | dispatcher = 路由器 ≠ 执行器 |
| 5 | 问用户业务问题（AskUser） | dispatcher = 无状态路由（**中断超限除外**） |

### 中断超限的 AskUser 例外

| 场景 | 操作 |
|------|------|
| `interrupt_budget <= 0` 且用户继续触发中断 | `next_agent = AskUser`，消息："interrupt_budget 已耗尽（5/5），是否授权额外中断？" |
| 授权后 | `interrupt_budget` 重置为 5，继续路由到 `INTERRUPT_REVIEW` |
| 拒绝后 | 强制继续当前 phase，不响应中断请求 |

## 四、与其他 Skill 边界

| Skill | 关系 |
|-------|------|
| `ad-tdd/SKILL.md` | **被调用**——PLAN/CODE 阶段由 ad-tdd 执行 TDD 循环 |
| `coding-standards.mdc` | **被引用**——L0-L6 质量门禁在 VERIFY 阶段强制跑 |
| `pr-gate/SKILL.md` | **被引用**——SIGN_OFF 阶段末尾跑 pr-gate 7 项 |
| `golden-set/SKILL.md` | **被引用**——REGRESSION 阶段触发 `--mode pr` |
| `frontend-standards/SKILL.md` | **被引用**——前端任务的 developer 角色触发 |

## 五、参考

- 路由协议真源：`agents/harness/DISPATCHER.md`
- 状态机：`harness/workflow-v2.yaml`（V2 唯一真源）
- 兼容旧版：`harness/workflow.yaml`（V1.6，迁移期只读，V2 稳定后冻结）
- phase context：`harness/context/`（6 个新 phase 落地前暂用 `phase-checklist.md` 合一份）
- evidence schema：`harness/evidence/README.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
