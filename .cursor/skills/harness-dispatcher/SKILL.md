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
| **task_type 指定** | "bugfix"/"refactor"/"doc-fix"/"perf-optimize" → 跳转对应 phase 子集 |

> **不触发**：让改一个 bug / 跑一个单测 / 看一段代码——属 `coding-standards` + `pr-gate`，不走 harness。

## 二、task_type 路由（V3 新增）

### 2.1 5 种任务类型

| task_type | 说明 | phase 子集 |
|-----------|------|----------|
| `feature` | 完整功能开发（默认） | PRD → ARCH_DESIGN → PRE_MORTEM → ATDD → PLAN → CODE → VERIFY → SECURITY_TEST → DEPLOY → REGRESSION → SIGN_OFF → DATA_REPLAY → INCIDENT_RESPONSE → OPS_LOOP → SKILL_UPDATE |
| `bugfix` | Bug 修复 | CODE → VERIFY → DEPLOY → REGRESSION → SIGN_OFF |
| `refactor` | 代码重构 | PLAN → CODE → VERIFY → REGRESSION → SIGN_OFF |
| `doc-fix` | 文档修复 | CODE → VERIFY → SIGN_OFF |
| `perf-optimize` | 性能优化 | PLAN → CODE → VERIFY → DEPLOY → REGRESSION → SIGN_OFF |

### 2.2 路由决策

```python
def get_next_phase(task_type: str, current_phase: str, workflow: dict) -> str | None:
    phases = workflow["task_types"][task_type]["phases"]
    idx = phases.index(current_phase) if current_phase in phases else -1
    if idx == -1 or idx + 1 >= len(phases):
        return None  # 流水线结束
    return phases[idx + 1]
```

### 2.3 初始 run 创建

创建新 run 时，根据用户意图推断 task_type：

| 关键词 | task_type |
|--------|-----------|
| "新功能" / "feature" / "开发" | `feature` |
| "bug" / "修复" / "fix" | `bugfix` |
| "重构" / "refactor" | `refactor` |
| "文档" / "doc" / "说明" | `doc-fix` |
| "性能" / "优化" / "perf" | `perf-optimize` |

## 三、调用协议（6 步 + task_type）

1. **Read** `harness/state/harness-state.json`（不存在则 `next_agent = orchestrator` 初始化）
2. **Read** `harness/workflow-v2.yaml`（V3 含 task_types 定义，**不再读** `workflow.yaml`）
3. **task_type 推断**：
   - 从用户消息推断 task_type（如 "修复 bug" → `bugfix`）
   - 或使用 `state.json.task_type`
4. **中断检查**：若用户显式触发"中断/暂停/interrupt"，且当前 phase `interruptible: true`：
   - 读取当前 `interrupt_budget`
   - 若 `interrupt_budget <= 0`，返回 `next_agent = AskUser` 请求授权超限
   - 否则：`interrupt_budget - 1`，记录 `interrupted_phase`，`next_agent = quality-guardian`
5. **task_type 路由**：
   - 根据 `task_type` 获取允许的 phase 列表（`workflow.task_types[task_type].phases`）
   - 只在该列表内的 phase 之间路由
   - exit_criteria 全满足 → 在 phase 列表中找到下一个 phase
   - exit_criteria 未满足 → 当前 phase `entry_agent`
6. **结束判定**：
   - 当前 phase 是 task_type phases 列表最后一个 → `DONE`
   - DATA_REPLAY 完成后 → 回到 task_type 的初始 phase（如 `bugfix` 直接 DONE）
   - INTERRUPT_REVIEW 完成后 → 恢复 `resume_from` 指向的 phase
7. 返回结构化指令：

| 字段 | 值 |
|------|---|
| task_type | `<feature|bugfix|refactor|doc-fix|perf-optimize>` |
| run_id | `<uuid>` |
| current_phase | `<name>` |
| next_agent | `<role-name 或 DONE 或 AskUser>` |
| context_to_load | `harness/context/phase-checklist.md` |
| evidence_required | `harness/evidence/<phase>.md` |

8. 调 `<next_agent>`（参考 `agents/harness/<FILE>.md`）；按需 Read 上述 context；evidence 落点由对应 agent 写

### task_type × phase context 映射表

> **约束**：不是所有 phase 都对每种 task_type 开放。Dispatcher 只在 `workflow.task_types[<task_type>].phases` 列表内的 phase 之间路由。

| phase | feature | bugfix | refactor | doc-fix | perf-optimize |
|-------|---------|--------|----------|---------|---------------|
| PRD | ✅ | ❌ | ❌ | ❌ | ❌ |
| ARCH_DESIGN | ✅ | ❌ | ❌ | ❌ | ❌ |
| PRE_MORTEM | ✅ | ❌ | ❌ | ❌ | ❌ |
| ATDD | ✅ | ❌ | ❌ | ❌ | ❌ |
| PLAN | ✅ | ❌ | ✅ | ❌ | ✅ |
| CODE | ✅ | ✅ | ✅ | ✅ | ✅ |
| VERIFY | ✅ | ✅ | ✅ | ✅ | ✅ |
| SECURITY_TEST | ✅ | ❌ | ❌ | ❌ | ❌ |
| DEPLOY | ✅ | ✅ | ❌ | ❌ | ✅ |
| REGRESSION | ✅ | ✅ | ✅ | ❌ | ✅ |
| SIGN_OFF | ✅ | ✅ | ✅ | ✅ | ✅ |
| DATA_REPLAY | ✅ | ❌ | ❌ | ❌ | ❌ |
| INCIDENT_RESPONSE | ✅ | ❌ | ❌ | ❌ | ❌ |
| OPS_LOOP | ✅ | ❌ | ❌ | ❌ | ❌ |
| SKILL_UPDATE | ✅ | ❌ | ❌ | ❌ | ❌ |
| INTERRUPT_REVIEW | ✅ | ✅ | ✅ | ✅ | ✅ |

> **INTERRUPT_REVIEW 特殊**：所有 task_type 均可进入，用于中断处理。

### task_type 路由示例

| task_type | 当前 phase | exit_criteria | 下一个 phase |
|-----------|-----------|---------------|--------------|
| bugfix | CODE | 全 PASS | VERIFY |
| bugfix | VERIFY | 全 PASS | DEPLOY |
| bugfix | REGRESSION | 全 PASS | SIGN_OFF |
| bugfix | SIGN_OFF | 全 PASS | **DONE** |
| doc-fix | CODE | 全 PASS | VERIFY |
| doc-fix | VERIFY | 全 PASS | SIGN_OFF |
| doc-fix | SIGN_OFF | 全 PASS | **DONE** |

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

## 五、输出契约

Dispatcher **只输出**以下 JSON 对象（不含任何业务文字描述，避免污染主会话上下文）：

```json
{
  "task_type": "bugfix",
  "next_agent": "developer",
  "phase": "CODE",
  "must_read_context": "harness/context/phase-checklist.md",
  "must_read_skills": [".cursor/rules/coding-standards.mdc"],
  "write_evidence_to": "harness/evidence/06-code.md",
  "state_update": {
    "task_type": "bugfix",
    "current_phase": "CODE",
    "current_agent": "developer",
    "exit_criteria_met": [false, false]
  }
}
```

字段语义：

- `task_type` — 任务类型（V3 新增）
- `next_agent` — 本轮唯一可被主会话调用的角色 ID
- `phase` — 对应 `workflow-v2.yaml` 的 `phases[].id`
- `must_read_context` — 阶段上下文文件
- `write_evidence_to` — 本 phase 必须写入的 evidence 文件路径
- `state_update` — 同步写入 `harness-state.json` 的字段

## 六、与其他 Skill 边界

| Skill | 关系 |
|-------|------|
| `ad-tdd/SKILL.md` | **被调用**——PLAN/CODE 阶段由 ad-tdd 执行 TDD 循环 |
| `coding-standards.mdc` | **被引用**——L0-L6 质量门禁在 VERIFY 阶段强制跑 |
| `pr-gate/SKILL.md` | **被引用**——SIGN_OFF 阶段末尾跑 pr-gate 7 项 |
| `golden-set/SKILL.md` | **被引用**——REGRESSION 阶段触发 `--mode pr` |
| `frontend-standards/SKILL.md` | **被引用**——前端任务的 developer 角色触发 |

## 七、参考

- 路由协议真源：`agents/harness/DISPATCHER.md`
- 状态机：`harness/workflow-v2.yaml`（V3 含 task_types 定义）
- task_type schema：`harness/state/harness-state.schema.md`
- 兼容旧版：`harness/workflow.yaml`（V1.6，迁移期只读）
- evidence schema：`harness/evidence/README.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
