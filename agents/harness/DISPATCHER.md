# R2-marker: protocol-only, no business thresholds allowed
---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-dispatcher
---

# DISPATCHER — Harness 路由协议

> 与阿里 Harness 原文对齐点：**"交通警察，只管路由不管业务"**。
> Dispatcher 是状态机控制器，**唯一职责**是把当前 `phase` 映射到下一个 `entry_agent`，
> **不**读取 evidence 内容、**不**写业务代码、**不**做跨阶段调度。

---

## 一、职责边界（与原文对齐）

| 维度 | Dispatcher 做 | Dispatcher **不做** |
|------|--------------|-------------------|
| 读取 | `harness/state/harness-state.json`、`harness/workflow-v2.yaml` | 任何 `evidence/*.md`、任何业务代码（`backend/`、`apps/`） |
| 写入 | `harness/state/harness-state.json`（仅 phase 字段、agent 字段、updated_at） | 任何 evidence 文件、任何业务代码、任何 Skill 内容 |
| 决策 | 根据 `current_phase` + `exit_criteria` 命中情况 → 输出 1 条 `next_agent` 指令 | 评审 evidence 内容、合并多角色观点、问用户澄清问题 |
| 调用 | 由主会话在每轮消息首句 Read 唯一 | 自己启动子 agent、自己跑测试 |

> **强约束**：本协议属于 `agents/harness/` 协议层文件，**不含**任何业务阈值（如 `if score > 0.8`），
> 业务规则仍按 `project-prohibitions.mdc` R-2 红线统一放 `backend/app/rules/`（YAML + 纯 Python 解释器）。

---

## 二、输入契约

| 输入 | 路径 | 必填 | 说明 |
|------|------|:---:|------|
| 当前状态 | `harness/state/harness-state.json` | ✅ | 含 `task_type`、`current_phase`、`run_id`、`updated_at`、`exit_criteria_met` |
| 状态机定义 | `harness/workflow-v2.yaml` | ✅ | 5 种 task_type + 16 阶段定义 + entry_agent 映射 + exit_criteria + interruption_policy |
| 上轮 phase 的 exit_criteria 命中信号 | 由 verifier / orchestrator 写入 state.json | ✅ | 布尔数组，逐条对应 workflow-v2.yaml 的 `exit_criteria` |

state.json schema（V3）：

```json
{
  "run_id": "FR-DIAG-02-20260717",
  "version": "3.0",
  "task_type": "bugfix",
  "current_phase": "CODE",
  "current_agent": "developer",
  "phase_started_at": "2026-07-17T22:00:00+08:00",
  "exit_criteria_met": [true, true],
  "next_phase_hint": null,
  "updated_at": "2026-07-17T22:01:23+08:00"
}
```

---

## 三、输出契约：单条 `next_agent` 指令

Dispatcher **只输出**以下 JSON 对象（不含任何业务文字描述，避免污染主会话上下文）：

```json
{
  "task_type": "bugfix",
  "next_agent": "verifier",
  "phase": "VERIFY",
  "must_read_context": "harness/context/phase-checklist.md",
  "must_read_skills": [".cursor/rules/coding-standards.mdc"],
  "write_evidence_to": "harness/evidence/07-verify.md",
  "state_update": {
    "task_type": "bugfix",
    "current_phase": "VERIFY",
    "current_agent": "verifier",
    "exit_criteria_met": [false, false]
  }
}
```

字段语义：

- `task_type` — 任务类型（V3 新增，决定 phase 子集）
- `next_agent` — 本轮唯一可被主会话调用的角色 ID（与 `agents/harness/REVIEWERS.md` / `EXECUTORS.md` 一致）
- `phase` — 对应 `workflow-v2.yaml` 的 `phases[].id`
- `must_read_context` — 阶段上下文文件（按需 Read，**不是**常驻）
- `write_evidence_to` — 本 phase 必须写入的 evidence 文件路径
- `state_update` — 同步写入 `harness-state.json` 的字段

## 三.b、task_type 路由约束（V3 新增）

> **核心约束**：不是所有 phase 都对每种 task_type 开放。Dispatcher 只在 `workflow.task_types[<task_type>].phases` 列表内的 phase 之间路由。

### 5 种 task_type × phase 子集

| task_type | phases | initial_phase |
|-----------|--------|---------------|
| `feature` | PRD, ARCH_DESIGN, PRE_MORTEM, ATDD, PLAN, CODE, VERIFY, SECURITY_TEST, DEPLOY, REGRESSION, SIGN_OFF, DATA_REPLAY, INCIDENT_RESPONSE, OPS_LOOP, SKILL_UPDATE | PRD |
| `bugfix` | CODE, VERIFY, DEPLOY, REGRESSION, SIGN_OFF | CODE |
| `refactor` | PLAN, CODE, VERIFY, REGRESSION, SIGN_OFF | PLAN |
| `doc-fix` | CODE, VERIFY, SIGN_OFF | CODE |
| `perf-optimize` | PLAN, CODE, VERIFY, DEPLOY, REGRESSION, SIGN_OFF | PLAN |

### 路由决策伪代码

```python
def get_next_phase(task_type: str, current_phase: str, workflow: dict) -> str | None:
    """根据 task_type 和当前 phase 计算下一个 phase。

    Args:
        task_type: 任务类型（如 "bugfix"）
        current_phase: 当前 phase（如 "CODE"）
        workflow: 读自 harness/workflow-v2.yaml

    Returns:
        下一个 phase，或 None（流水线结束 → DONE）
    """
    phases = workflow["task_types"][task_type]["phases"]
    if current_phase not in phases:
        return None  # 当前 phase 不在 task_type 允许列表中（异常）
    idx = phases.index(current_phase)
    if idx + 1 >= len(phases):
        return None  # 流水线结束
    return phases[idx + 1]
```

### 特殊 phase 路由

| 场景 | 路由规则 |
|------|---------|
| `INTERRUPT_REVIEW` 完成 | 恢复 `resume_from` 指向的 phase |
| `DATA_REPLAY` 完成 | 回到 task_type 的 initial_phase（`bugfix/doc-fix` 直接 DONE） |
| `SIGN_OFF` 完成 | DONE（所有 task_type 通用） |

## 三.c、exit_criteria 真实判定逻辑

> **V2 修复**：替代原 `[false, false, false]` 占位符。Dispatcher 现在执行每条 shell 命令，全部 exit code 0 才视为 phase 完成。
> **真源**：`harness/workflow-v2.yaml` 的 `phases[].exit_criteria`（16 个 phase 各自 3 条命令）。
> **执行器**：`harness/scripts/check_phase.py`（**S1 跨平台已实现**，PowerShell / bash / Linux 通用）。

### 判定流程（伪代码）

```python
def is_phase_complete(current_phase: str, workflow: dict) -> bool:
    """通过执行 shell 命令判定 phase 是否完成。

    实现位置：harness/scripts/check_phase.py（349 行跨平台 Python）

    Args:
        current_phase: 当前 phase ID（如 "PRD"）
        workflow: 读自 harness/workflow-v2.yaml 的 phases 列表

    Returns:
        True = 全部 exit_criteria 命令返回 exit code 0
        False = 任一命令失败

    支持命令（POSIX 子集，PowerShell 兼容）：
      - test -f/-d/-e/-s/-r PATH        （Python `_builtin_test` 等价实现）
      - grep -q/-qE/-E PATTERN FILE     （Python `_builtin_grep` 等价实现）
      - 其他 shell 命令：fallback 到 subprocess.run
    """
    phase_def = next(p for p in workflow["phases"] if p["id"] == current_phase)
    commands = phase_def["exit_criteria"]  # e.g. ["test -f ...", "grep -q ...", "..."]

    for cmd in commands:
        result = run_exit_criterion(cmd, cwd=PROJECT_ROOT)  # noqa: F821
        if not result.ok:
            log(f"phase={current_phase} cmd={cmd} FAIL exit={result.returncode}")
            return False

    log(f"phase={current_phase} exit_criteria ALL PASS")
    return True
```

### 使用方式

```bash
# CLI 用法（在 PowerShell / bash 任意环境）
python harness/scripts/check_phase.py PRD            # 单 phase 判定（verbose 推荐加 --verbose）
python harness/scripts/check_phase.py --all          # 全部 16 phase 判定 + SUMMARY
python harness/scripts/check_phase.py --list         # 仅列出所有 phase
python harness/scripts/check_phase.py --json         # JSON 输出（供 CI 解析）

# Dispatcher 集成（无论 AI 还是 verifier/dispatcher 都通过这个调用）
exit_code = subprocess.run([sys.executable, 'harness/scripts/check_phase.py', current_phase],
                            cwd=PROJECT_ROOT).returncode
```

### 状态更新规则

| 场景 | action |
|------|--------|
| 全部 exit_criteria 命令 exit 0 | 根据 task_type phases 列表找到下一个 phase；更新 `state.json.current_phase` 和 `current_agent` |
| exit_criteria 全满足且是 task_type phases 列表最后一个 | `next_phase = DONE` |
| 任一命令非 0 | 维持 `current_phase` 不变；记录失败命令到 `state.json.last_failure`；触发对应 reviewer 重写 evidence |
| `auto_mode: true`（一人模式默认） | 连续运行不打断；`exit_criteria` 全部 PASS 后自动推进到 next phase |
| `auto_mode: false` | 每 phase 末尾输出 "phase X 完成，是否进入下一 phase？" 等待用户确认 |

### 一人模式特殊行为

`workflow-v2.yaml` 的 `one_person_mode.enabled: true` 时：

- PRE_MORTEM / SIGN_OFF 启用 `one_person_synthesis: true`，**跳过 5 reviewer 串行**，改为 orchestrator 单次自动摘要
- 其他 phase 默认 `auto_mode: true`，连续推进无需用户介入
- 只有 `INTERRUPT_REVIEW`（询问型 phase）和用户主动说 "暂停" 时才中断

### 跨平台兼容 ✅ S1 已解决

`exit_criteria` 命令由 **`harness/scripts/check_phase.py` 统一执行**，不再依赖本地 shell：

| 平台 | 状态 |
|---|---|
| Linux / macOS bash | ✅ 原生兼容 |
| Windows PowerShell | ✅ `_builtin_test` / `_builtin_grep` Python 等价实现 |
| WSL bash | ✅ 原生兼容 |
| CI runner（GitHub Actions） | ✅ `pr-gate-ci.yml` 新增 harness-exit-criteria job（详见 5.5.3） |

**关键设计**：
1. check_phase.py **不依赖任何 bash/grep/test 可执行文件**——只用 Python 标准库 + PyYAML
2. bash builtin（`test`、`[`、`grep`）Python 重实现，避免 Windows 下 `FileNotFoundError`
3. fallback 到 `subprocess.run(cmd_parts, shell=False)` 执行其它命令
4. 超时 10s，捕获 stderr 并截断 200 字符，避免长路径污染日志

**Phase 命令兼容性规则**（未来新增 exit_criteria 必须遵循）：
1. 优先用 `test` / `grep` builtin（已原生支持）
2. 避免 `awk` / `sed` / `xargs` / `find`（需要单独包装）
3. 引用路径用**正斜杠** `harness/evidence/01-requirement.md`（Python `Path` 自动兼容 Windows `\`）

---

## 四、决策表（V2 16 阶段 → entry_agent）

> `workflow-v2.yaml` 是 V2 真源。PRE_MORTEM / SIGN_OFF 的 `entry_agent` 是合法的首个 reviewer；随后必须按 `dispatch.reviewers` 串行调用五个 reviewer，最后由 `orchestrator` 合成，不能省略任何一个。
> `INTERRUPT_REVIEW` 只在可打断 phase 收到追问时进入；完成后恢复 `$interrupted_phase`，不把中断 review 当作业务主流程的线性终态。

| current_phase | entry_agent | next_phase(s) | must_read_context | write_evidence_to |
|---|---|---|---|---|
| `PRD` | `requirement-analyst` | `ARCH_DESIGN` | `harness/context/phase-checklist.md` | `evidence/01-requirement.md` |
| `ARCH_DESIGN` | `tech-architect` | `PRE_MORTEM` | `harness/context/phase-checklist.md` | `evidence/02-tech-design.md` |
| `PRE_MORTEM` | `requirement-analyst` → `tech-architect` → `quality-guardian` → `security-reviewer` → `devops-reviewer` → `orchestrator` | `ATDD` | `harness/context/phase-checklist.md` | `harness/evidence/03*.md` + `harness/evidence/04-pre-mortem.md` |
| `ATDD` | `quality-guardian` | `PLAN` | `harness/context/phase-checklist.md` | `evidence/03-quality.md` |
| `PLAN` | `plan-generator` | `CODE` | `harness/context/phase-checklist.md` | `evidence/05-plan.md` |
| `CODE` | `developer` | `VERIFY` | `harness/context/phase-checklist.md` | `evidence/06-code.md` |
| `VERIFY` | `verifier` | `SECURITY_TEST` | `harness/context/phase-checklist.md` | `evidence/05-verification.md` |
| `SECURITY_TEST` | `security-reviewer` | `DEPLOY` | `harness/context/phase-checklist.md` | `harness/evidence/08-security-test.md` |
| `DEPLOY` | `deployer` | `REGRESSION` | `harness/context/phase-checklist.md` | `evidence/06-deploy.md` |
| `REGRESSION` | `tester` | `SIGN_OFF` | `harness/context/phase-checklist.md` | `evidence/07-regression.md` |
| `SIGN_OFF` | `requirement-analyst` → `tech-architect` → `quality-guardian` → `security-reviewer` → `devops-reviewer` → `orchestrator` | `INCIDENT_RESPONSE` | `harness/context/phase-checklist.md` | `harness/evidence/09-signoff.md` |
| `DATA_REPLAY` | `requirement-analyst` | `PRD` | `harness/context/phase-checklist.md` | `harness/evidence/12-data-replay.md` |
| `INCIDENT_RESPONSE` | `deployer` | `OPS_LOOP` | `harness/context/phase-checklist.md` | `harness/evidence/13-incident-response.md` |
| `OPS_LOOP` | `tester` | `SKILL_UPDATE` | `harness/context/phase-checklist.md` | `harness/evidence/14-ops-loop.md` |
| `SKILL_UPDATE` | `quality-guardian` | `INTERRUPT_REVIEW` | `harness/context/phase-checklist.md` | `harness/evidence/15-skill-update.md` |
| `INTERRUPT_REVIEW` | `quality-guardian` | resume `$interrupted_phase` | `harness/context/phase-checklist.md` | `harness/evidence/16-interrupt-review.md` |

> `workflow-v2.yaml` 中的 `next: null` 仅表示 `INTERRUPT_REVIEW` 不拥有固定业务后继；它按 `resume_from` 恢复被打断的 phase。`SKILL_UPDATE` 完成后的 `INTERRUPT_REVIEW` 用于本轮收尾检查，随后恢复到 `DATA_REPLAY`，再开始下一轮。

---

## 五、硬禁止清单（R2 + 上下文隔离）

| # | 禁止行为 | 触发后果 |
|---|---------|---------|
| 1 | Read 任何 `harness/evidence/*.md` | 主会话上下文超 8K；越过 orchestrator / 评审角色职责 |
| 2 | Write 任何业务代码（`backend/app/`、`apps/`） | 越过 developer 阶段；违反 R-5 工具铁则 |
| 3 | 跨阶段调度（跳过 PRE_MORTEM 直接 ATDD） | 评审证据未签字就进入编码，PR-Gate 会拒绝合入 |
| 4 | 在决策表外动态判定 next_agent | 状态机漂移；workflow-v2.yaml 失去唯一真源地位 |
| 5 | 把 evidence 内容回传到主会话 | 主会话"忍不住"自己决策，违反上下文隔离铁律 |

> 兜底机制：`agents/harness/` 内任意文件被 grep `if.*score.*>` 必须无命中
> （与 `project-prohibitions.mdc` R-2 同款 grep，由 pr-gate harness-evidence Skill 执行）。

---

## 六、退出条件

Dispatcher 在以下任一情况下终止本轮：

1. 输出 `next_agent` 指令并已写入 `harness-state.json`（**唯一允许的写操作**）
2. 当前 phase 为 `INTERRUPT_REVIEW` 且 review evidence 完成 → 恢复 `resume_from` 指向的 phase；若无中断栈则进入 `DATA_REPLAY`
3. 当前 phase 为 `DATA_REPLAY` 且 `exit_criteria_met` 全为 true → 进入新一轮 `PRD`
4. 状态机文件缺失或字段不合法 → 返回错误指令并要求 orchestrator / 主会话先修复骨架

---

## 七、与其他协议文件的关系

`DISPATCHER.md`（本文件）只 Read `workflow-v2.yaml` + `state.json`，只 Write `state.json`（元数据）。
不接触 `ORCHESTRATOR.md` / `REVIEWERS.md` / `EXECUTORS.md` 的内容——所有业务判断由它们各自负责。

## 八、参考

- 状态机：`harness/workflow-v2.yaml`（V3 含 task_types 定义）
- task_type schema：`harness/state/harness-state.schema.md`
- 兼容旧版：`harness/workflow.yaml`（V1.6，迁移期只读）
- Skill：`.cursor/skills/harness-dispatcher/SKILL.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
