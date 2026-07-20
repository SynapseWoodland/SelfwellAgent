# Harness State Schema（V3）

> **V3 更新**：新增 `task_type` 字段，支持 5 种任务类型（feature/bugfix/refactor/doc-fix/perf-optimize）。
> **V2 更新**：`interrupt_budget`、`interrupt_stack`、`replay_session_id`、`run_metadata` 字段。
> **唯一真源**：本文件描述 schema；运行期状态见 `harness/state/harness-state.json`。
> **V1.6/V2 兼容**：V1.6/V2 state.json 缺少 V3 字段时，默认填充 `null`；V3 dispatcher 读取时会用默认值初始化。

## 一、完整 Schema（JSON Schema Draft-07）

### 1.1 task_types 定义（V3 新增）

```yaml
task_types:
  feature:       # 完整功能开发
    phases: [REQUIREMENT, ARCH_DESIGN, PRE_MORTEM, ATDD, PLAN, CODE, VERIFY, SECURITY_TEST, DEPLOY, REGRESSION, SIGN_OFF, DATA_REPLAY, INCIDENT_RESPONSE, OPS_LOOP, SKILL_UPDATE]
  bugfix:        # Bug 修复
    phases: [CODE, VERIFY, DEPLOY, REGRESSION, SIGN_OFF]
  refactor:      # 代码重构
    phases: [PLAN, CODE, VERIFY, REGRESSION, SIGN_OFF]
  doc-fix:       # 文档修复
    phases: [CODE, VERIFY, SIGN_OFF]
  perf-optimize: # 性能优化
    phases: [PLAN, CODE, VERIFY, DEPLOY, REGRESSION, SIGN_OFF]
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
      "description": "任务类型，决定执行哪些 phase 子集（V3 新增）"
    },
    "run_id": {
      "type": "string",
      "pattern": "^FR-[A-Z]+-\\d{2}-\\d{8}$",
      "description": "Feature run ID，格式：FR-<DOMAIN>-<NN>-<YYYYMMDD>"
    },
    "version": {
      "type": "string",
      "const": "3.0",
      "description": "Harness 版本，V3 = 3.0（支持 task_type）"
    },
    "current_phase": {
      "type": "string",
      "enum": ["REQUIREMENT", "ARCH_DESIGN", "PRE_MORTEM", "ATDD", "PLAN", "CODE", "VERIFY", "SECURITY_TEST", "DEPLOY", "REGRESSION", "SIGN_OFF", "DATA_REPLAY", "INCIDENT_RESPONSE", "OPS_LOOP", "SKILL_UPDATE", "INTERRUPT_REVIEW"],
      "description": "当前 phase（受 task_type 约束，只执行 task_type.phases 中的 phase）"
    },
    "current_agent": {
      "type": "string",
      "enum": ["requirement-analyst", "tech-architect", "quality-guardian", "security-reviewer", "devops-reviewer", "developer", "verifier", "deployer", "tester", "orchestrator"],
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
      "description": "exit_criteria 命中状态数组，对应 workflow-v2.yaml 的 phase.exit_criteria"
    },
    "next_phase_hint": {
      "type": ["string", "null"],
      "description": "下一个 phase 提示（V2 新增：DATA_REPLAY 完成后为 auto-cycle-to-PRD）"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "最后更新时间（ISO 8601）"
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
          "const": "interrupt_budget",
          "description": "budget 字段名"
        },
        "replay_field": {
          "type": "string",
          "const": "replay_session_id",
          "description": "replay session 字段名"
        }
      }
    },
    "interrupt_budget": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5,
      "description": "剩余中断次数，初始 5，每进入 INTERRUPT_REVIEW 减 1"
    },
    "interrupt_stack": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["phase", "agent", "interrupted_at"],
        "properties": {
          "phase": {
            "type": "string",
            "description": "被打断的 phase"
          },
          "agent": {
            "type": "string",
            "description": "被打断时的 agent"
          },
          "interrupted_at": {
            "type": "string",
            "format": "date-time",
            "description": "中断时间"
          },
          "reason": {
            "type": ["string", "null"],
            "description": "中断原因摘要（可选）"
          }
        }
      },
      "description": "中断栈，用于追踪嵌套中断（V2 新增）"
    },
    "replay_session_id": {
      "type": ["string", "null"],
      "format": "uuid",
      "description": "当前 replay session ID，DATA_REPLAY phase 触发时生成新 UUID（V2 新增）"
    },
    "run_metadata": {
      "type": "object",
      "description": "run 元数据（V2 新增）",
      "properties": {
        "task_type": {
          "type": "string",
          "enum": ["feature", "bugfix", "refactor", "doc-fix", "perf-optimize"],
          "description": "任务类型（V3 新增，与顶层 task_type 一致）"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "description": "run 创建时间"
        },
        "created_by": {
          "type": "string",
          "description": "run 创建者（user 或 agent ID）"
        },
        "feature": {
          "type": ["string", "null"],
          "description": "feature 名称（若有）"
        },
        "parent_run_id": {
          "type": ["string", "null"],
          "description": "父 run ID（用于追踪 replay 链路）"
        }
      }
    },
    "phase_history": {
      "type": "array",
      "description": "phase 历史，用于审计",
      "items": {
        "type": "object",
        "required": ["phase", "entered_at", "exited_at"],
        "properties": {
          "phase": {
            "type": "string",
            "description": "phase 名称"
          },
          "agent": {
            "type": "string",
            "description": "负责的 agent"
          },
          "entered_at": {
            "type": "string",
            "format": "date-time",
            "description": "进入时间"
          },
          "exited_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "退出时间（null 表示当前 phase）"
          },
          "evidence_ref": {
            "type": ["string", "null"],
            "description": "evidence 文件路径"
          },
          "interrupt_budget_at_exit": {
            "type": ["integer", "null"],
            "description": "退出时的 interrupt_budget"
          }
        }
      }
    }
  }
}
```

## 二、示例（V3 完整）

```json
{
  "run_id": "FR-DIAG-02-20260718",
  "version": "2.0",
  "task_type": "feature",
  "current_phase": "CODE",
  "current_agent": "developer",
  "phase_started_at": "2026-07-18T21:00:00+08:00",
  "exit_criteria_met": [true, true, false],
  "next_phase_hint": null,
  "updated_at": "2026-07-18T21:30:00+08:00",
  "interrupt_policy": {
    "budget_per_run": 5,
    "escalation": "AskUser",
    "review_phase": "INTERRUPT_REVIEW",
    "budget_field": "interrupt_budget",
    "replay_field": "replay_session_id"
  },
  "interrupt_budget": 4,
  "interrupt_stack": [
    {
      "phase": "ARCH_DESIGN",
      "agent": "tech-architect",
      "interrupted_at": "2026-07-18T20:00:00+08:00",
      "reason": "用户追问架构选型"
    }
  ],
  "replay_session_id": null,
  "run_metadata": {
    "created_at": "2026-07-18T09:00:00+08:00",
    "created_by": "user",
    "feature": "diagnosis-v2-pipeline",
    "parent_run_id": null
  },
  "phase_history": [
    {
      "phase": "PRD",
      "agent": "requirement-analyst",
      "entered_at": "2026-07-18T09:00:00+08:00",
      "exited_at": "2026-07-18T10:30:00+08:00",
      "evidence_ref": "harness/evidence/01-requirement.md",
      "interrupt_budget_at_exit": 5
    },
    {
      "phase": "ARCH_DESIGN",
      "agent": "tech-architect",
      "entered_at": "2026-07-18T10:30:00+08:00",
      "exited_at": "2026-07-18T14:00:00+08:00",
      "evidence_ref": "harness/evidence/02-tech-design.md",
      "interrupt_budget_at_exit": 4
    },
    {
      "phase": "CODE",
      "agent": "developer",
      "entered_at": "2026-07-18T21:00:00+08:00",
      "exited_at": null,
      "evidence_ref": null,
      "interrupt_budget_at_exit": null
    }
  ]
}
```

## 三、V1.6 → V2 迁移默认值

| V2 新增字段 | 默认值 | 来源 |
|-------------|--------|------|
| `version` | `"1.6"` | V1.6 state.json 无此字段 |
| `interrupt_budget` | `null` | V1.6 无中断机制 |
| `interrupt_stack` | `[]` | V1.6 无中断栈 |
| `replay_session_id` | `null` | V1.6 无 replay |
| `run_metadata` | `null` | V1.6 无元数据 |
| `next_phase_hint` | `null` | 向后兼容 |

V2 dispatcher 在读取 V1.6 state.json 时，会自动补充默认值：

```python
# V2 dispatcher 读取 state.json 时
if state.get("version") != "2.0":
    state.setdefault("interrupt_budget", 5)
    state.setdefault("interrupt_stack", [])
    state.setdefault("replay_session_id", None)
    state.setdefault("run_metadata", None)
    state.setdefault("next_phase_hint", None)
    state["version"] = "2.0"  # 标记已迁移
```

## 四、字段写入权限

| 字段 | dispatcher | orchestrator | 主会话 |
|------|------------|---------------|--------|
| `current_phase` | ✅ | ✅ | ❌ |
| `current_agent` | ✅ | ✅ | ❌ |
| `phase_started_at` | ✅ | ✅ | ❌ |
| `exit_criteria_met` | ❌ | ✅ | ❌ |
| `next_phase_hint` | ✅ | ✅ | ❌ |
| `updated_at` | ✅ | ✅ | ❌ |
| `interrupt_budget` | ✅（中断时） | ✅ | ❌ |
| `interrupt_stack` | ✅（中断时） | ✅ | ❌ |
| `replay_session_id` | ✅（DATA_REPLAY 时） | ✅ | ❌ |
| `phase_history` | ❌ | ✅ | ❌ |

## 五、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`
- evidence schema：`harness/evidence/README.md`
- dispatcher 协议：`agents/harness/DISPATCHER.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
