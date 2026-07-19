---
name: harness-context-phase-checklist
description: >
  Harness 16 phase context 合并为 5 列表格（V2 含 6 个新 phase）。
  当 dispatcher 路由到任一 phase 时由主会话按需 Read。
disable-model-invocation: true
---

# Phase Checklist（V2：16 phase）

> **V2 更新**：6 个新 phase（SECURITY_TEST / INCIDENT_RESPONSE / OPS_LOOP / SKILL_UPDATE / DATA_REPLAY / INTERRUPT_REVIEW）已加入速查表。
> 阶段切换时 dispatcher **不重新加载**本文件，仅更新 `state.json.current_phase`。
> V2 新 phase 的详细 context 见 `harness/context/NN-<phase>.md`。

## 一、16 阶段 × 5 字段速查表

| 阶段 | 必读（≤4 项） | 禁用 | 必产物 | 退出 |
|------|--------------|------|--------|------|
| **PRD** | `docs/PRD/*`、`SELFWELL-MVP-SRS.md`、`SPEC-A0`、`workflow-v2.yaml` | 写代码 / 改 state.json / 读其他 context | `evidence/01-requirement.md` + state.json 更新 | FR 编号全覆盖 + 每个 FR ≥1 场景 |
| **ARCH_DESIGN** | `evidence/01-requirement.md`、`SPEC-A0`、`SPEC-HEADER-TEMPLATE`、`docs/adr/README` | 写代码 / 改 state.json / 读 PRD 原文 | TDS 骨架 + `evidence/02-tech-design.md` + ADR 草案 | 引用 ≥1 ADR + FR 一一映射 + frontmatter 8 字段 |
| **PRE_MORTEM** | `evidence/0[1-2]-*.md`、`TDS-M*.md`、3 份模板 | 写代码 / 改 state.json / 跨 phase evidence | `evidence/03-pre-mortem.md`（3 必签 + 2 触发签字） | 3 评审签字 + orchestrator 合成 |
| **ATDD** | `evidence/01-04*.md`、`TDS-M*.md`、3 份模板 | 写代码 / 改 state.json | `evidence/04-atdd.md`（≥1 Gherkin 三态覆盖） | ATDD 字段映射 openapi |
| **PLAN** | `evidence/04-atdd.md`、`TDS-M*.md`、`coding-standards` | 写代码 / 改 state.json | `evidence/05-plan.md` | 实施计划含时间估算 |
| **CODE** | `evidence/05-plan.md`、`TDS-M*.md`、`coding-standards` | 读 PRD 原文 / 改 state.json | `evidence/06-code.md` | L0-L6 门禁全 PASS |
| **VERIFY** | `evidence/06-code.md`、`TDS-M*.md` | 读 PRD 原文 / 改 state.json | `evidence/07-verify.md` | 所有 TDS test pass |
| **SECURITY_TEST**（V2） | `evidence/06-*.md`、`evidence/07-verify.md`、`coding-standards/RULES.md` | 写代码 / 读 PRD 原文 | `evidence/08-security-test.md` | bandit 无 S/F + PII 合规 |
| **DEPLOY** | `evidence/07-verify.md`、`evidence/08-*.md` | 读 PRD 原文 / 改 state.json | `evidence/09-deploy.md` | 部署验证通过 |
| **REGRESSION** | `evidence/09-deploy.md` | 读 PRD 原文 / 改 state.json | `evidence/10-regression.md` | 回归测试全 PASS |
| **SIGN_OFF** | `evidence/10-*.md`、pr-gate | 读 PRD 原文 / 改 state.json | `evidence/11-signoff.md`（5 评审签字） | PR-Gate 7 项全 PASS |
| **DATA_REPLAY**（V2） | `evidence/11-signoff.md`、`docs/PRD/*` | 忽略 PRD 偏差 | `evidence/12-data-replay.md` | 偏差已记录 + `replay_session_id` 已生成 |
| **INCIDENT_RESPONSE**（V2） | `evidence/11-signoff.md`、`evidence/09-deploy.md` | 跳过根因 / 未通知 stakeholder | `evidence/13-incident-response.md` | 冷静期已过 + stakeholder 已通知 |
| **OPS_LOOP**（V2） | `evidence/13-*.md`、`evidence/11-signoff.md` | 跳过灰度 / 修改 A/B | `evidence/14-ops-loop.md` | 统计显著性达成 |
| **SKILL_UPDATE**（V2） | `evidence/14-*.md`、`harness/lessons/`、`harness-autolearn` | 强制晋升 | `evidence/15-skill-update.md` | lesson 沉淀 + 晋升判断已记录 |
| **INTERRUPT_REVIEW**（V2） | `harness-state.json`、`evidence/<interrupted_phase>.md` | 修改被中断 evidence | `evidence/16-interrupt-review.md` | 决策已执行（继续/推迟/升级） |

> V2 新 phase（SECURITY_TEST / DATA_REPLAY / INCIDENT_RESPONSE / OPS_LOOP / SKILL_UPDATE / INTERRUPT_REVIEW）的详细 context 见 `harness/context/NN-<phase>.md`。

## 二、Pre-Mortem 签字触发式扩展规则

| 触发条件 | 必追加签字 |
|----------|----------|
| 涉及 PII / LLM 调用 / 对外 API / 密钥 | security-reviewer |
| 涉及 CI 配置 / 部署 / 数据库迁移 / 基础设施 | devops-reviewer |
| 涉及 覆盖率 / 门禁 / ATDD | quality-guardian（必签之一） |

未触发角色显式填"无意见 / 不适用"。

## 三、与其他文件的边界

- 本文件**只**列出阶段规则；具体模板路径见 `harness/templates/`
- 状态机定义见 `harness/workflow-v2.yaml`（V2 唯一真源）
- 兼容旧版：`harness/workflow.yaml`（V1.6，迁移期只读）
- 角色协议见 `agents/harness/{DISPATCHER,ORCHESTRATOR,REVIEWERS,EXECUTORS}.md`
- evidence schema 见 `harness/evidence/README.md`（V2 8 字段）

## 四、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`（V2 唯一真源）
- evidence 真源：`harness/evidence/README.md`（V2 8 字段）
- V2 新 phase 详细 context：`harness/context/NN-<phase>.md`
- 红线兜底：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
