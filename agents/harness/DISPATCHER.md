# R2-marker: protocol-only, no business thresholds allowed
---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-dispatcher
---

# DISPATCHER — Harness V3 路由协议

> 与阿里 Harness 原文对齐点：**"交通警察，只管路由不管业务"**。
> Dispatcher 是状态机控制器，**唯一职责**是把当前 `phase` 映射到下一个 `entry_agent`，
> **不**读取 evidence 内容、**不**写业务代码、**不**做跨阶段调度。

---

## 一、职责边界（与原文对齐）

| 维度 | Dispatcher 做 | Dispatcher **不做** |
|------|--------------|-------------------|
| 读取 | `harness/state/harness-state.json`、`harness/workflow-v3.yaml` | 任何 `evidence/*.md`、任何业务代码 |
| 写入 | `harness/state/harness-state.json`（仅 phase 字段、agent 字段、updated_at） | 任何 evidence 文件、任何业务代码 |
| 决策 | 根据 `current_phase` + `exit_criteria` 命中情况 → 输出 1 条 `next_agent` 指令 | 评审 evidence 内容、合并多角色观点、问用户澄清问题 |
| 调用 | 由主会话在每轮消息首句 Read 唯一 | 自己启动子 agent、自己跑测试 |

> **强约束**：本协议属于 `agents/harness/` 协议层文件，**不含**任何业务阈值，
> 业务规则仍按 `project-prohibitions.mdc` R-2 红线统一放 `backend/app/rules/`。

---

## 二、输入契约

| 输入 | 路径 | 必填 | 说明 |
|------|------|:---:|------|
| 当前状态 | `harness/state/harness-state.json` | ✅ | 含 `task_type`、`current_phase`、`run_id`、`updated_at`、`exit_criteria_met`、`rejection_count` |
| 状态机定义 | `harness/workflow-v3.yaml` | ✅ | 6 种 task_type + 24 阶段定义 + entry_agent 映射 + exit_criteria + review_policy |

state.json schema（V3）：

```json
{
  "run_id": "FR-DIAG-02-20260724",
  "version": "3.0",
  "task_type": "feature",
  "current_phase": "REVIEW_ARCH",
  "current_agent": "tech-architect",
  "phase_started_at": "2026-07-24T10:00:00+08:00",
  "exit_criteria_met": [true, true, true],
  "rejection_count": 0,
  "next_phase_hint": null,
  "updated_at": "2026-07-24T10:01:23+08:00"
}
```

---

## 三、输出契约：单条 `next_agent` 指令

Dispatcher **只输出**以下 JSON 对象：

```json
{
  "task_type": "feature",
  "next_agent": "tech-architect",
  "phase": "REVIEW_ARCH",
  "must_read_context": "harness/context/phase-checklist.md",
  "must_read_skills": [".cursor/rules/coding-standards.mdc"],
  "write_evidence_to": "harness/evidence/review-arch.md",
  "state_update": {
    "task_type": "feature",
    "current_phase": "REVIEW_ARCH",
    "current_agent": "tech-architect",
    "exit_criteria_met": [false, false, false],
    "rejection_count": 0
  }
}
```

字段语义：

- `task_type` — 任务类型
- `next_agent` — 本轮唯一可被主会话调用的角色 ID
- `phase` — 对应 `workflow-v3.yaml` 的 `phases[].id`
- `must_read_context` — 阶段上下文文件
- `write_evidence_to` — 本 phase 必须写入的 evidence 文件路径
- `state_update` — 同步写入 `harness-state.json` 的字段

---

## 四、task_type 路由约束

### 6 种 task_type × phase 子集

| task_type | phases | initial_phase |
|-----------|--------|---------------|
| `feature` | REQUIREMENT → REVIEW_SRS → ARCH_DESIGN → REVIEW_ARCH → ATDD → REVIEW_ATDD → TDS → REVIEW_TDS → PLAN → REVIEW_PLAN → PRE_MORTEM → CODE → DEPLOY → VERIFY → SECURITY_TEST → REGRESSION → SIGN_OFF → DATA_REPLAY → INCIDENT_RESPONSE → OPS_LOOP → SKILL_UPDATE | REQUIREMENT |
| `bugfix` | CODE → DEPLOY → VERIFY → SECURITY_TEST → REGRESSION → SIGN_OFF | CODE |
| `refactor` | PLAN → CODE → DEPLOY → VERIFY → SECURITY_TEST → REGRESSION → SIGN_OFF | PLAN |
| `doc-fix` | DOC_FIX → SIGN_OFF | DOC_FIX |
| `perf-optimize` | PLAN → CODE → DEPLOY → VERIFY → SECURITY_TEST → REGRESSION → SIGN_OFF | PLAN |

### 路由决策伪代码

```python
def get_next_phase(task_type: str, current_phase: str, workflow: dict) -> str | None:
    """
    根据 task_type 和当前 phase 计算下一个 phase。

    Args:
        task_type: 任务类型（如 "feature"）
        current_phase: 当前 phase（如 "REVIEW_ARCH"）
        workflow: 读自 harness/workflow-v3.yaml

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
| `ARCH_CLARIFICATION` 完成 | 返回触发它的 Review 节点，重新进入 Review |
| `DATA_REPLAY` 完成 | 回到 task_type 的 initial_phase（`bugfix/doc-fix` 直接 DONE） |
| `SIGN_OFF` 完成 | DONE（所有 task_type 通用） |

---

## 五、Review 路由与 3次打回机制

### 5.1 Review 节点识别

V3 中所有以 `REVIEW_` 开头的 phase 是 Review 节点：

```
REVIEW_SRS | REVIEW_ARCH | REVIEW_ATDD | REVIEW_TDS | REVIEW_PLAN
```

### 5.2 3次打回机制（review_policy）

```python
MAX_REJECTIONS = 3

def handle_review_rejection(current_phase: str, state: dict) -> str:
    """
    处理 Review 节点打回逻辑。

    规则：
    1. Review 不通过 → rejection_count += 1
    2. rejection_count < MAX_REJECTIONS → 回到对应 phase 重新修改
    3. rejection_count >= MAX_REJECTIONS → 触发 ARCH_CLARIFICATION
    """
    rejection_count = state.get("rejection_count", 0) + 1

    if rejection_count >= MAX_REJECTIONS:
        return "ARCH_CLARIFICATION"
    else:
        # 回到触发 Review 的 phase
        return get_producing_phase(current_phase)

def get_producing_phase(review_phase: str) -> str:
    """获取 Review 对应的生产 phase。"""
    mapping = {
        "REVIEW_SRS": "REQUIREMENT",
        "REVIEW_ARCH": "ARCH_DESIGN",
        "REVIEW_ATDD": "ATDD",
        "REVIEW_TDS": "TDS",
        "REVIEW_PLAN": "PLAN",
    }
    return mapping.get(review_phase, review_phase)
```

### 5.3 Review 节点 → entry_agent 映射

| Review 节点 | 负责角色 | 审查的文档 |
|------------|----------|------------|
| `REVIEW_SRS` | requirement-analyst | SRS 文档 |
| `REVIEW_ARCH` | tech-architect | 架构设计文档 |
| `REVIEW_ATDD` | quality-guardian | ATDD 文档 |
| `REVIEW_TDS` | tech-architect | TDS 文档 |
| `REVIEW_PLAN` | plan-generator | PLAN 文档 |

### 5.4 ARCH_CLARIFICATION 流程

```
Review 打回（3次）
     ↓
触发 ARCH_CLARIFICATION
     ↓
tech-architect 输出架构澄清提案 + 选项建议
     ↓
用户确认方案
     ↓
更新对应文档
     ↓
再次进入对应 Review
```

---

## 六、决策表（V3 24 阶段）

| current_phase | entry_agent | next_phase(s) | write_evidence_to |
|---------------|-------------|---------------|------------------|
| `REQUIREMENT` | requirement-analyst | `REVIEW_SRS` | `evidence/01-requirement.md` |
| `REVIEW_SRS` | requirement-analyst | `ARCH_DESIGN` / `ARCH_CLARIFICATION` | `evidence/review-srs.md` |
| `ARCH_DESIGN` | tech-architect | `REVIEW_ARCH` | `evidence/02-tech-design.md` |
| `REVIEW_ARCH` | tech-architect | `ATDD` / `ARCH_CLARIFICATION` | `evidence/review-arch.md` |
| `ATDD` | quality-guardian | `REVIEW_ATDD` | `evidence/03-atdd.md` |
| `REVIEW_ATDD` | quality-guardian | `TDS` / `ARCH_CLARIFICATION` | `evidence/review-atdd.md` |
| `TDS` | tech-architect | `REVIEW_TDS` | `evidence/04-tds.md` |
| `REVIEW_TDS` | tech-architect | `PLAN` / `ARCH_CLARIFICATION` | `evidence/review-tds.md` |
| `PLAN` | plan-generator | `REVIEW_PLAN` | `evidence/05-plan.md` |
| `REVIEW_PLAN` | plan-generator | `PRE_MORTEM` / `ARCH_CLARIFICATION` | `evidence/review-plan.md` |
| `PRE_MORTEM` | requirement-analyst | `CODE` | `evidence/06-pre-mortem.md` |
| `CODE` | developer | `DEPLOY` | `evidence/07-code.md` |
| `DEPLOY` | deployer | `VERIFY` | `evidence/09-deploy.md` |
| `VERIFY` | verifier | `REGRESSION` | `evidence/10-verify.md` |
| `SECURITY_TEST` | security-reviewer | `REGRESSION` | `evidence/11-security-test.md` |
| `REGRESSION` | tester | `SIGN_OFF` | `evidence/12-regression.md` |
| `SIGN_OFF` | requirement-analyst | `INCIDENT_RESPONSE` | `evidence/13-signoff.md` |
| `DATA_REPLAY` | requirement-analyst | `REQUIREMENT` | `evidence/14-data-replay.md` |
| `INCIDENT_RESPONSE` | deployer | `OPS_LOOP` | `evidence/15-incident-response.md` |
| `OPS_LOOP` | tester | `SKILL_UPDATE` | `evidence/16-ops-loop.md` |
| `SKILL_UPDATE` | quality-guardian | `INTERRUPT_REVIEW` | `evidence/17-skill-update.md` |
| `ARCH_CLARIFICATION` | tech-architect | 回触发 Review | `evidence/arch-clarification.md` |
| `INTERRUPT_REVIEW` | quality-guardian | resume `$interrupted_phase` | `evidence/18-interrupt-review.md` |

---

## 七、exit_criteria 判定逻辑

### 7.1 判定流程

```python
def is_phase_complete(current_phase: str, workflow: dict) -> bool:
    """
    通过执行 shell 命令判定 phase 是否完成。

    Args:
        current_phase: 当前 phase ID（如 "REVIEW_SRS"）
        workflow: 读自 harness/workflow-v3.yaml 的 phases 列表

    Returns:
        True = 全部 exit_criteria 命令返回 exit code 0
        False = 任一命令失败
    """
    phase_def = next(p for p in workflow["phases"] if p["id"] == current_phase)
    commands = phase_def["exit_criteria"]

    for cmd in commands:
        result = run_exit_criterion(cmd, cwd=PROJECT_ROOT)
        if not result.ok:
            log(f"phase={current_phase} cmd={cmd} FAIL exit={result.returncode}")
            return False

    log(f"phase={current_phase} exit_criteria ALL PASS")
    return True
```

### 7.2 Review 节点特殊判定

Review 节点需要额外的对齐检查：

```python
def is_review_complete(review_phase: str, evidence_path: str) -> bool:
    """
    Review 节点完成判定。

    除了 exit_criteria，还需要验证：
    1. alignment_check: PASS | ARCH_CLARIFICATION
    2. rejection_count < MAX_REJECTIONS
    """
    # 1. 检查对齐标记
    alignment = read_frontmatter_field(evidence_path, "alignment_check")
    if alignment == "ARCH_CLARIFICATION":
        return False  # 需要触发架构澄清

    # 2. 检查打回次数
    rejection_count = read_frontmatter_field(evidence_path, "rejection_count", 0)
    if rejection_count >= MAX_REJECTIONS:
        return False  # 触发架构澄清

    # 3. 执行标准 exit_criteria
    return run_standard_exit_criteria(review_phase)
```

---

## 八、一人与多角色模式

### 8.1 一人模式（auto_mode: true）

- 所有 Review 节点默认 `auto_mode: true`
- PRE_MORTEM / SIGN_OFF 启用 `one_person_synthesis: true`
- ARCH_CLARIFICATION 强制升级给用户确认

### 8.2 评审深度配置

| 深度 | 说明 | 用于 |
|------|------|------|
| `light` | 场景格式、Given-When-Then、覆盖度 | REVIEW_ATDD, REVIEW_PLAN |
| `medium` | 加上唯一真源检查、业务/技术对齐 | REVIEW_SRS, REVIEW_TDS |
| `heavy` | 加上架构方案选择、与用户澄清 | REVIEW_ARCH |

---

## 九、硬禁止清单

| # | 禁止行为 | 触发后果 |
|---|---------|---------|
| 1 | Read 任何 `harness/evidence/*.md` | 主会话上下文超限 |
| 2 | Write 任何业务代码 | 越过 developer 阶段 |
| 3 | 跳过 Review 直接进入下一阶段 | PR-Gate 拒绝合入 |
| 4 | Review 节点不打回直接通过 | 违反 Review 职责 |
| 5 | 超过 3次打回不触发 ARCH_CLARIFICATION | 违反 review_policy |
| 6 | ARCH_CLARIFICATION 不升级给用户确认 | 违反架构澄清机制 |

---

## 十、参考

- 状态机：`harness/workflow-v3.yaml`（V3 含 24 phase）
- task_type schema：`harness/state/harness-state.schema.md`
- 兼容旧版：`harness/workflow-v2.yaml`（V2，迁移期只读）
- Skill：`.cursor/skills/harness-dispatcher/SKILL.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
