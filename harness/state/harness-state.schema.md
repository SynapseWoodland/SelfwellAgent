# Harness State Schema（V3）

> **V3 更新**：新增 Review 节点 + TDS 阶段 + 3次打回机制 + ARCH_CLARIFICATION
> **V2 更新**：`interrupt_budget`、`interrupt_stack`、`replay_session_id`、`run_metadata` 字段。
> **唯一真源**：本文件描述 schema；运行期状态见 `harness/state/harness-state.json`。

## 一、完整 Schema（JSON Schema Draft-07）

### 1.1 task_types 定义（V3）

```yaml
task_types:
  feature:
    phases:
      - REQUIREMENT
      - REVIEW_SRS
      - ARCH_DESIGN
      - REVIEW_ARCH
      - ATDD
      - REVIEW_ATDD
      - TDS
      - REVIEW_TDS
      - PLAN
      - REVIEW_PLAN
      - PRE_MORTEM
      - CODE
      - DEPLOY
      - VERIFY
      - SECURITY_TEST
      - REGRESSION
      - SIGN_OFF
      - DATA_REPLAY
      - INCIDENT_RESPONSE
      - OPS_LOOP
      - SKILL_UPDATE
  bugfix:
    phases: [CODE, DEPLOY, VERIFY, SECURITY_TEST, REGRESSION, SIGN_OFF]
  refactor:
    phases: [PLAN, CODE, DEPLOY, VERIFY, SECURITY_TEST, REGRESSION, SIGN_OFF]
  doc-fix:
    phases: [DOC_FIX, SIGN_OFF]
  perf-optimize:
    phases: [PLAN, CODE, DEPLOY, VERIFY, SECURITY_TEST, REGRESSION, SIGN_OFF]
```

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HarnessStateV3",
  "type": "object",
  "required": ["run_id", "current_phase", "current_agent", "version", "interrupt_policy", "task_type"],
  "properties": {
    "task_type": {
      "type": "string",
      "enum": ["feature", "bugfix", "refactor", "doc-fix", "perf-optimize"],
      "description": "任务类型，决定执行哪些 phase 子集（V3）"
    },
    "run_id": {
      "type": "string",
      "pattern": "^FR-[A-Z]+-\\d{2}-\\d{8}$",
      "description": "Feature run ID，格式：FR-<DOMAIN>-<NN>-<YYYYMMDD>"
    },
    "version": {
      "type": "string",
      "const": "3.0",
      "description": "Harness 版本，V3 = 3.0"
    },
    "current_phase": {
      "type": "string",
      "enum": [
        "REQUIREMENT", "REVIEW_SRS", "ARCH_DESIGN", "REVIEW_ARCH",
        "ATDD", "REVIEW_ATDD", "TDS", "REVIEW_TDS",
        "PLAN", "REVIEW_PLAN", "PRE_MORTEM", "CODE",
        "DEPLOY", "VERIFY", "SECURITY_TEST", "REGRESSION",
        "SIGN_OFF", "DATA_REPLAY", "INCIDENT_RESPONSE",
        "OPS_LOOP", "SKILL_UPDATE", "ARCH_CLARIFICATION",
        "INTERRUPT_REVIEW"
      ],
      "description": "当前 phase（受 task_type 约束）"
    },
    "current_agent": {
      "type": "string",
      "enum": [
        "requirement-analyst", "tech-architect", "quality-guardian",
        "security-reviewer", "developer", "verifier", "deployer",
        "tester", "orchestrator", "plan-generator"
      ],
      "description": "当前负责的 agent 角色"
    },
    "phase_started_at": {
      "type": "string",
      "format": "date-time",
      "description": "当前 phase 开始时间（ISO 8601）"
    },
    "exit_criteria_met": {
      "type": "array",
      "items": { "type": "boolean" },
      "description": "exit_criteria 命中状态数组"
    },
    "rejection_count": {
      "type": "integer",
      "minimum": 0,
      "maximum": 3,
      "description": "当前 Review 节点打回次数（V3 新增）"
    },
    "next_phase_hint": {
      "type": ["string", "null"],
      "description": "下一个 phase 提示"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "最后更新时间（ISO 8601）"
    },
    "review_policy": {
      "type": "object",
      "description": "Review 策略配置（V3 新增）",
      "properties": {
        "max_rejections": {
          "type": "integer",
          "const": 3,
          "description": "单个 Review 节点最多打回 3 次"
        },
        "escalation_on_exhausted": {
          "type": "string",
          "const": "ARCH_CLARIFICATION",
          "description": "3次打回后触发架构澄清"
        },
        "track_in_state": {
          "type": "boolean",
          "const": true,
          "description": "在 state 中追踪打回次数"
        }
      }
    },
    "interrupt_policy": {
      "type": "object",
      "required": ["budget_per_run", "escalation", "review_phase"],
      "properties": {
        "budget_per_run": {
          "type": "integer",
          "const": 5,
          "description": "每 run 最大中断次数，固定 5"
        },
        "escalation": {
          "type": "string",
          "const": "AskUser",
          "description": "超预算升级方式"
        },
        "review_phase": {
          "type": "string",
          "const": "INTERRUPT_REVIEW",
          "description": "中断审查 phase"
        },
        "budget_field": {
          "type": "string",
          "const": "interrupt_budget"
        },
        "replay_field": {
          "type": "string",
          "const": "replay_session_id"
        }
      }
    },
    "interrupt_budget": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5,
      "description": "剩余中断次数，初始 5"
    },
    "interrupt_stack": {
      "type": "array",
      "description": "中断栈，用于追踪嵌套中断",
      "items": {
        "type": "object",
        "required": ["phase", "agent", "interrupted_at"],
        "properties": {
          "phase": { "type": "string" },
          "agent": { "type": "string" },
          "interrupted_at": { "type": "string", "format": "date-time" },
          "reason": { "type": ["string", "null"] }
        }
      }
    },
    "replay_session_id": {
      "type": ["string", "null"],
      "format": "uuid",
      "description": "当前 replay session ID"
    },
    "run_metadata": {
      "type": "object",
      "properties": {
        "task_type": {
          "type": "string",
          "enum": ["feature", "bugfix", "refactor", "doc-fix", "perf-optimize"]
        },
        "created_at": { "type": "string", "format": "date-time" },
        "created_by": { "type": "string" },
        "feature": { "type": ["string", "null"] },
        "parent_run_id": { "type": ["string", "null"] }
      }
    },
    "phase_history": {
      "type": "array",
      "description": "phase 历史，用于审计",
      "items": {
        "type": "object",
        "required": ["phase", "entered_at", "exited_at"],
        "properties": {
          "phase": { "type": "string" },
          "agent": { "type": "string" },
          "entered_at": { "type": "string", "format": "date-time" },
          "exited_at": { "type": ["string", "null"], "format": "date-time" },
          "evidence_ref": { "type": ["string", "null"] },
          "interrupt_budget_at_exit": { "type": ["integer", "null"] },
          "rejection_count": { "type": "integer", "description": "该 phase 的打回次数（V3 新增）" }
        }
      }
    },
    "arch_clarification_history": {
      "type": "array",
      "description": "架构澄清历史（V3 新增）",
      "items": {
        "type": "object",
        "required": ["triggered_at", "triggering_review", "resolution"],
        "properties": {
          "triggered_at": { "type": "string", "format": "date-time" },
          "triggering_review": {
            "type": "string",
            "enum": ["REVIEW_SRS", "REVIEW_ARCH", "REVIEW_ATDD", "REVIEW_TDS", "REVIEW_PLAN"]
          },
          "rejection_count": { "type": "integer" },
          "options_provided": { "type": "array", "items": { "type": "string" } },
          "user_selected_option": { "type": ["string", "null"] },
          "resolution": {
            "type": "string",
            "enum": ["ACCEPTED", "MODIFIED", "REJECTED"]
          },
          "resolved_at": { "type": ["string", "null"], "format": "date-time" }
        }
      }
    }
  }
}
```

---

## 二、示例（V3 feature 流程）

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
  "updated_at": "2026-07-24T10:30:00+08:00",
  "review_policy": {
    "max_rejections": 3,
    "escalation_on_exhausted": "ARCH_CLARIFICATION",
    "track_in_state": true
  },
  "interrupt_policy": {
    "budget_per_run": 5,
    "escalation": "AskUser",
    "review_phase": "INTERRUPT_REVIEW",
    "budget_field": "interrupt_budget",
    "replay_field": "replay_session_id"
  },
  "interrupt_budget": 5,
  "interrupt_stack": [],
  "replay_session_id": null,
  "run_metadata": {
    "task_type": "feature",
    "created_at": "2026-07-24T09:00:00+08:00",
    "created_by": "user",
    "feature": "diagnosis-v2-pipeline",
    "parent_run_id": null
  },
  "phase_history": [
    {
      "phase": "REQUIREMENT",
      "agent": "requirement-analyst",
      "entered_at": "2026-07-24T09:00:00+08:00",
      "exited_at": "2026-07-24T09:30:00+08:00",
      "evidence_ref": "harness/evidence/01-requirement.md",
      "interrupt_budget_at_exit": 5,
      "rejection_count": 0
    },
    {
      "phase": "REVIEW_SRS",
      "agent": "requirement-analyst",
      "entered_at": "2026-07-24T09:30:00+08:00",
      "exited_at": "2026-07-24T09:45:00+08:00",
      "evidence_ref": "harness/evidence/review-srs.md",
      "interrupt_budget_at_exit": 5,
      "rejection_count": 0
    },
    {
      "phase": "ARCH_DESIGN",
      "agent": "tech-architect",
      "entered_at": "2026-07-24T09:45:00+08:00",
      "exited_at": "2026-07-24T10:00:00+08:00",
      "evidence_ref": "harness/evidence/02-tech-design.md",
      "interrupt_budget_at_exit": 5,
      "rejection_count": 0
    },
    {
      "phase": "REVIEW_ARCH",
      "agent": "tech-architect",
      "entered_at": "2026-07-24T10:00:00+08:00",
      "exited_at": null,
      "evidence_ref": null,
      "interrupt_budget_at_exit": null,
      "rejection_count": 0
    }
  ],
  "arch_clarification_history": []
}
```

---

## 三、V2 → V3 迁移默认值

| V3 新增字段 | 默认值 | 说明 |
|-------------|--------|------|
| `rejection_count` | `0` | Review 节点打回次数 |
| `review_policy` | `{max_rejections: 3, ...}` | Review 策略配置 |
| `arch_clarification_history` | `[]` | 架构澄清历史 |

---

## 四、Review 节点打回机制

### 4.1 rejection_count 语义

| 值 | 含义 |
|----|------|
| `0` | 首次进入该 Review 节点 |
| `1` | 被打回 1 次，已返回生产 phase 修改 |
| `2` | 被打回 2 次，已返回生产 phase 修改 |
| `3` | **触发 ARCH_CLARIFICATION** |

### 4.2 Review 节点 → 生产 phase 映射

| Review 节点 | 生产 phase | 负责角色 |
|-------------|------------|----------|
| `REVIEW_SRS` | `REQUIREMENT` | requirement-analyst |
| `REVIEW_ARCH` | `ARCH_DESIGN` | tech-architect |
| `REVIEW_ATDD` | `ATDD` | quality-guardian |
| `REVIEW_TDS` | `TDS` | tech-architect |
| `REVIEW_PLAN` | `PLAN` | plan-generator |

---

## 五、字段写入权限

| 字段 | dispatcher | orchestrator | 主会话 |
|------|------------|---------------|--------|
| `current_phase` | ✅ | ✅ | ❌ |
| `current_agent` | ✅ | ✅ | ❌ |
| `phase_started_at` | ✅ | ✅ | ❌ |
| `exit_criteria_met` | ❌ | ✅ | ❌ |
| `rejection_count` | ✅（Review 时） | ✅ | ❌ |
| `next_phase_hint` | ✅ | ✅ | ❌ |
| `updated_at` | ✅ | ✅ | ❌ |
| `interrupt_budget` | ✅（中断时） | ✅ | ❌ |
| `interrupt_stack` | ✅（中断时） | ✅ | ❌ |
| `phase_history` | ❌ | ✅ | ❌ |
| `arch_clarification_history` | ❌ | ✅ | ❌ |

---

## 六、参考

- workflow-v3.yaml：`harness/workflow-v3.yaml`
- evidence schema：`harness/evidence/README.md`
- dispatcher 协议：`agents/harness/DISPATCHER.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
