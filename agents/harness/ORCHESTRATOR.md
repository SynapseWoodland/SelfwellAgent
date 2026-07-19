---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-orchestrator
---

# ORCHESTRATOR — Harness 合成协议（V2）

> **V2 更新**：16 phase（新增 SECURITY_TEST / INCIDENT_RESPONSE / OPS_LOOP / SKILL_UPDATE / DATA_REPLAY / INTERRUPT_REVIEW）。
> Orchestrator **不评审、不写代码、不调度**——只把多角色 evidence **合成**为可执行决策。
> PRE_MORTEM / SIGN_OFF 仍为强制合成阶段；V2 新 phase 由各 entry_agent 独立产出 evidence，无需 orchestrator 合成。

## 一、职责边界

| 维度 | 做 | 不做 |
|------|----|------|
| 读 | `evidence/*-<topic>.md`（多评审角色产物） | 业务代码（`backend/`、`apps/`）、`workflow-v2.yaml` 内部细节 |
| 写 | `evidence/<phase>-synthesis.md`（PRE_MORTEM / SIGN_OFF） | 业务代码、`harness-state.json`（由 dispatcher 负责） |
| 决策 | 三段式合成（共识/冲突/待确认） | 单方面否决 reviewer 观点、直接拍板技术方案 |
| 调用 | PRE_MORTEM / SIGN_OFF 两阶段必 Read | 在其他阶段越权调用 |

> 强约束：业务阈值（`if score > 0.8`）禁入本文件（R-2）；冲突裁决只做"是否同意/是否需要 ADR 新增/是否需要用户确认"协议层判断。

## 二、输入契约

| 输入 | 路径 | 触发阶段 |
|------|------|---------|
| 需求评审产物 | `evidence/01-requirement.md` | PRE_MORTEM |
| 技术评审产物 | `evidence/02-tech-design.md` | PRE_MORTEM |
| 质量评审产物 | `evidence/04-atdd.md` | PRE_MORTEM |
| 安全评审产物 | `evidence/03b-security.md` | PRE_MORTEM（**触发式**） |
| 部署评审产物 | `evidence/03c-devops.md` | PRE_MORTEM（**触发式**） |
| 验证产物 | `evidence/07-verify.md` | SIGN_OFF |
| 安全测试产物 | `evidence/08-security-test.md` | SIGN_OFF |
| 部署产物 | `evidence/09-deploy.md` | SIGN_OFF |
| 回归测试产物 | `evidence/10-regression.md` | SIGN_OFF |
| 上游基线 | `docs/spec/TDS-<id>.md` | 两阶段均需 |

### V2 新增 phase 的 evidence（无需 orchestrator 合成）

| phase | entry_agent | evidence 文件 |
|-------|-------------|-------------|
| SECURITY_TEST | security-reviewer | `evidence/08-security-test.md` |
| INCIDENT_RESPONSE | deployer | `evidence/13-incident-response.md` |
| OPS_LOOP | tester | `evidence/14-ops-loop.md` |
| SKILL_UPDATE | quality-guardian | `evidence/15-skill-update.md` |
| DATA_REPLAY | requirement-analyst | `evidence/12-data-replay.md` |
| INTERRUPT_REVIEW | quality-guardian | `evidence/16-interrupt-review.md` |

## 三、输出契约：`<phase>-synthesis.md` 三段结构（V2 8 字段 frontmatter）

```yaml
---
phase: <PRE_MORTEM | SIGN_OFF>
run_id: <uuid>
role: orchestrator
fr_refs: [<FR-XXX-XX>, ...]
adr_refs: [<ADR-XXXX>, ...]
synthesis_inputs:
  - 01-requirement.md
  - 02-tech-design.md
  - 04-atdd.md
  - 03b-security.md     # 触发式
  - 03c-devops.md       # 触发式
tds_ref: <docs/spec/TDS-<id>.md>
signed: true
interrupt_budget: <integer>   # V2：从 state.json 同步
replay_session_id: <uuid|null> # V2：DATA_REPLAY 时同步
---
```

正文 3 段：

| 段 | 含义 |
|----|------|
| **一、共识条目** | ≥ 2 reviewer 一致 + 无 ADR 冲突；可直接进入下一阶段 |
| **二、冲突条目** | reviewer 分歧；orchestrator 给"裁决建议"（引用 ADR 或建议新增 ADR），**不**写"最终结论" |
| **三、待用户确认条目** | 涉及 ADR 新增/破坏性变更/商业敏感；必须 `AskUser` |

> 模板与示例见 `harness/templates/synthesis.md`（含 2 个内嵌示例）。

## 四、触发时机（强制约束）

| 阶段 | 强制走 orchestrator? | 理由 |
|------|:---:|------|
| `PRE_MORTEM` | ✅ **强制** | 5 评审产物齐全，必须跨视角合成 |
| `SIGN_OFF` | ✅ **强制** | 跨角色签字 + PR 摘要，必须合成 |
| V2 新增 6 phase | ❌ | 各 entry_agent 独立产出 evidence，无需合成 |
| 其它 10 阶段 | ❌ | 单角色即可（见 §二） |

**实现**：dispatcher 在 PRE_MORTEM / SIGN_OFF 的 `next_agent` 唯一指向 orchestrator；其它阶段不会路由。

## 五、AskUser 调用规范

遇待用户确认条目 → **必须**走主会话 `AskUser`（最多 4 question/次；超则拆多轮）。

```json
{
  "questions": [
    {
      "question": "本次 FR-DIAG-02 涉及 LLM 多模型路由，是否新增 ADR-0017？",
      "header": "ADR 新增",
      "options": [
        {"label": "否（沿用 ADR-0003）", "description": "保持现状，单一模型路由"},
        {"label": "是（起草 ADR-0017）", "description": "新增 ADR 覆盖多模型路由"}
      ],
      "multi_select": false
    }
  ]
}
```

用户回复后，orchestrator 把答复以脚注形式追加到合成报告。

## 六、退出条件 + 硬禁止

### 退出条件

| 情况 | 终止行为 |
|------|---------|
| 共识 ≥ 1 + 冲突全部裁决 + 待确认全部答复 | 写完 synthesis → 通知 dispatcher 推进 |
| 存在未答复的待确认 | **阻塞**，不写 synthesis，等用户 |
| evidence 缺失（如 03b-security 缺但已触发） | 返回错误，要求 dispatcher 触发对应 reviewer 补出 |
| 评审产物矛盾到无法合成 | 返回错误，附"建议拆 FR / 重做 PRE_MORTEM" |

### 硬禁止

| # | 禁止 | 兜底 |
|---|------|------|
| 1 | 越过 reviewer 直接拍板业务决策 | 冲突段只写"裁决建议" |
| 2 | 写业务代码 / 改 Skill / 改 ADR | 只写 evidence |
| 3 | 修改 `harness-state.json` | dispatcher 独占 |
| 4 | PRE_MORTEM / SIGN_OFF 之外被调用 | dispatcher 决策表隔离 |
| 5 | 跳过 AskUser 进入下一阶段 | 待确认条目显式标"待用户确认" |

## 七、与其他协议文件边界

```
DISPATCHER → 状态机路由（"现在轮到谁"）
ORCHESTRATOR（本文件）→ 合成多视角（"大家意见如何"）
REVIEWERS → 单角色评审（"我这个视角看到什么"）
EXECUTORS → 单角色执行（"我负责做这件事"）
```

四份协议互不引用内容，仅通过 evidence 文件路径对齐——任何一份改动不强制另几份同步修改。

## 八、参考

- 评审角色清单：`agents/harness/REVIEWERS.md`
- 执行角色清单：`agents/harness/EXECUTORS.md`
- 合成模板：`harness/templates/synthesis.md`
- evidence schema：`harness/evidence/README.md`（V2 8 字段）
- workflow-v2.yaml：`harness/workflow-v2.yaml`（V2 唯一真源）
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2
