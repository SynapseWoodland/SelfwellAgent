---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-orchestrator
---

# ORCHESTRATOR — Harness 合成协议（V3）

> **V3 更新**：新增 5 个 Review 节点 + TDS phase；证据路径迁移到 `templates/`。
> Orchestrator **不评审、不写代码、不调度**——只把多角色 evidence **合成**为可执行决策。
> PRE_MORTEM / SIGN_OFF 仍为强制合成阶段；其他 phase 由各 entry_agent 独立产出 evidence，无需 orchestrator 合成。

## 一、职责边界

| 维度 | 做 | 不做 |
|------|----|------|
| 读 | `templates/phase/*-<topic>.md`（多评审角色产物） | 业务代码（`backend/`、`apps/`）、`workflow-v3.yaml` 内部细节 |
| 写 | `templates/phase/03-pre-mortem.md`（PRE_MORTEM）、`templates/phase/11-signoff.md`（SIGN_OFF） | 业务代码、`harness-state.json`（由 dispatcher 负责） |
| 决策 | 三段式合成（共识/冲突/待确认） | 单方面否决 reviewer 观点、直接拍板技术方案 |
| 调用 | PRE_MORTEM / SIGN_OFF 两阶段必 Read | 在其他阶段越权调用 |

> 强约束：业务阈值（`if score > 0.8`）禁入本文件（R-2）；冲突裁决只做"是否同意/是否需要 ADR 新增/是否需要用户确认"协议层判断。

## 二、输入契约

| 输入 | 路径 | 触发阶段 |
|------|------|---------|
| 需求评审产物 | `templates/phase/01-requirement.md` | PRE_MORTEM |
| 技术评审产物 | `templates/phase/02-tech-design.md` | PRE_MORTEM |
| 质量评审产物 | `templates/phase/04-atdd.md` | PRE_MORTEM |
| 安全评审产物 | `templates/phase/08-security-test.md` | PRE_MORTEM（**触发式**） |
| 部署评审产物 | `templates/phase/09-deploy.md` | PRE_MORTEM（**触发式**） |
| 验证产物 | `templates/phase/07-verify.md` | SIGN_OFF |
| 安全测试产物 | `templates/phase/08-security-test.md` | SIGN_OFF |
| 部署产物 | `templates/phase/09-deploy.md` | SIGN_OFF |
| 回归测试产物 | `templates/phase/10-regression.md` | SIGN_OFF |
| 上游基线 | `docs/spec/TDS-<id>.md` | 两阶段均需 |

### V3 新增 phase 的 evidence（无需 orchestrator 合成）

| phase | entry_agent | evidence 文件 |
|-------|-------------|---------------|
| `REVIEW_SRS` | requirement-analyst | `templates/review/review-srs.md` |
| `REVIEW_ARCH` | tech-architect | `templates/review/review-arch.md` |
| `REVIEW_ATDD` | quality-guardian | `templates/review/review-atdd.md` |
| `REVIEW_TDS` | tech-architect | `templates/review/review-tds.md` |
| `REVIEW_PLAN` | plan-generator | `templates/review/review-plan.md` |
| `TDS` | tech-architect | `templates/phase/04-tds.md` |
| `ARCH_CLARIFICATION` | tech-architect | `templates/arch-clarification.md` |

## 三、输出契约：三段结构

```yaml
---
phase: <PRE_MORTEM | SIGN_OFF>
run_id: <uuid>
role: orchestrator
fr_refs: [<FR-XXX-XX>, ...]
adr_refs: [<ADR-XXXX>, ...]
synthesis_inputs:
  - templates/phase/01-requirement.md
  - templates/phase/02-tech-design.md
  - templates/phase/04-atdd.md
  - templates/phase/08-security-test.md     # 触发式
  - templates/phase/09-deploy.md           # 触发式
tds_ref: <docs/spec/TDS-<id>.md>
signed: true
interrupt_budget: <integer>   # 从 state.json 同步
replay_session_id: <uuid|null> # DATA_REPLAY 时同步
---
```

正文 3 段：

| 段 | 含义 |
|----|------|
| **一、共识条目** | ≥ 2 reviewer 一致 + 无 ADR 冲突；可直接进入下一阶段 |
| **二、冲突条目** | reviewer 分歧；orchestrator 给"裁决建议"（引用 ADR 或建议新增 ADR），**不**写"最终结论" |
| **三、待用户确认条目** | 涉及 ADR 新增/破坏性变更/商业敏感；必须 `AskUser` |

## 四、触发时机（强制约束）

| 阶段 | 强制走 orchestrator? | 理由 |
|------|:---:|------|
| `PRE_MORTEM` | ✅ **强制** | 5 评审产物齐全，必须跨视角合成 |
| `SIGN_OFF` | ✅ **强制** | 跨角色签字 + PR 摘要，必须合成 |
| 其他 19 个 phase | ❌ | 各 entry_agent 独立产出 evidence，无需合成 |

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
| evidence 缺失（如 security-test 缺但已触发） | 返回错误，要求 dispatcher 触发对应 reviewer 补出 |
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
- 合成模板：`harness/evidence/templates/phase/03-pre-mortem.md`
- evidence schema：`harness/evidence/README.md`（V3 结构）
- workflow-v3.yaml：`harness/workflow-v3.yaml`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2
