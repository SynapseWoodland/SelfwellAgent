---

## name: harness-context-phase-checklist

description: >
  Harness V3 24 phase context checklist。
  当 dispatcher 路由到任一 phase 时由主会话按需 Read。
disable-model-invocation: true

# Phase Checklist（V3：24 phase）

> **V3 更新**：新增 5 个 Review 节点 + TDS 阶段 + 3次打回 + ARCH_CLARIFICATION。
> 阶段切换时 dispatcher **不重新加载**本文件，仅更新 `state.json.current_phase`。

## 一、24 阶段 × 6 字段速查表

### A. 核心架构文档（必读）

| 文档 | 说明 | 来源 |
|------|------|------|
| `docs/architecture/tech-architecture-design-v3.md` | **V3 技术架构真源** | 唯一真源 |
| `docs/architecture/SELFWELL-MVP-SDS.md` | **MVP 系统设计规格说明书** | 核心设计 |
| `docs/architecture/4plus1-view-model.md` | **4+1 视图模型** | 架构全景 |
| `docs/architecture/api.yaml` | **OpenAPI 接口规格** | API 真源 |
| `docs/architecture/error-codes.md` | **错误码规范** | 错误码真源 |
| `docs/architecture/sse-events.md` | **SSE 事件契约** | 流式事件真源 |
| `docs/architecture/ddd-bounded-context.md` | **DDD 限界上下文** | 架构边界真源 |

### B. 决策记录（ADR）

| 文档 | 说明 | 来源 |
|------|------|------|
| `docs/architecture/adr/README.md` | **ADR 索引** | 所有决策记录入口 |
| `docs/architecture/adr/0001-tech-stack.md` | 技术栈决策 | ADR-0001 |
| `docs/architecture/adr/0003-llm-primary-fallback.md` | LLM 主备决策 | ADR-0003 |
| `docs/architecture/adr/0015-persona-contract.md` | Persona 契约 | ADR-0015 |
| `docs/architecture/adr/0016-feedback-unified.md` | Feedback 统一 | ADR-0016 |
| `docs/architecture/adr/0019-async-sse-pipeline.md` | 异步 SSE 管道 | ADR-0019 |

### C. 技术设计规格（TDS）

| 文档 | 说明 | 来源 |
|------|------|------|
| `docs/architecture/TDS/TDS-M1-wechat-login.md` | 微信登录 | M1 |
| `docs/architecture/TDS/TDS-M2-multimodal-diagnosis.md` | 多模态诊断 | M2 |
| `docs/architecture/TDS/TDS-M3-21day-plan.md` | 21 天计划 | M3 |
| `docs/architecture/TDS/TDS-M4-checkin-loop.md` | 打卡循环 | M4 |
| `docs/architecture/TDS/TDS-M5-persona-chat.md` | Persona 聊天 | M5 |

### D. 数据架构

| 文档 | 说明 | 来源 |
|------|------|------|
| `docs/architecture/data/data-architecture.md` | 数据架构 | 核心 |
| `docs/architecture/data/forbidden-words.md` | 禁用词 | 合规 |
| `docs/architecture/data/medical-reject-words.yaml` | 医疗拒绝词 | 合规 |

### E. 业务需求与合规

| 文档 | 说明 | 来源 |
|------|------|------|
| `docs/PRD/`* | 业务需求文档目录 | PRD 原文 |
| `docs/requirements/SELFWELL-MVP-SRS.md` | 系统需求规格说明书（SRS） | SRS 真源 |
| `docs/compliance/README.md` | 合规框架 | 合规索引 |

### F. 前端设计

| 文档 | 说明 | 来源 |
|------|------|------|
| `docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html` | **前端原型真源**（唯一） | V2 原型 |
| `docs/frontend-design/figma-pixso-spec/pages-v2/cursor-dev-spec.md` | **前端还原规范**（颜色/字号/布局 token） | AI 还原参考 |
| `docs/frontend-design/figma-pixso-spec/pages-v2/cursor-api-contract.md` | **API 接口契约**（前端调用规范） | 前端开发参考 |
| `docs/frontend-design/design-spec.md` | 设计规范 | 前端规范 |

### G. Evidence 文档来源字段说明

> **核心原则**：evidence 是变更追踪，不是完整文档。记录本轮改过的文档，改什么记什么，不改的不记。

| Evidence 文件 | 文档来源字段 | 说明 |
|-------------|-------------|------|
| `evidence/templates/phase/01-requirement.md` | `source_doc` / `created_from_scratch` | 引用已有 SRS 或从0创建 |
| `evidence/templates/phase/02-tech-design.md` | `source_sds` / `source_tds_modules` / `created_tds_modules` | 引用已有 SDS/TDS |
| `evidence/templates/phase/04-atdd.md` | `tds_ref` / `atdd_docs` | 关联 TDS + ATDD 列表 |


| 阶段                        | 必读（核心文档）                                                                                          | 合规/前端补充                                                                                                                                                            | 禁用                                    | 必产物                                            | 退出                                     |
| ------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------- | ---------------------------------------------- | -------------------------------------- |
| **REQUIREMENT** | `docs/PRD/*`、`workflow-v3.yaml` | — | 写代码 / 改 state.json / 读其他 context | `templates/phase/01-requirement.md` + state.json 更新 | FR 编号全覆盖 + 每个 FR ≥1 场景 |
| **REVIEW_SRS** | `templates/phase/01-requirement.md`、`workflow-v3.yaml` | — | 写代码 / 改 state.json | `templates/review/review-srs.md` | alignment_check: PASS |
| **ARCH_DESIGN** | `templates/phase/01-requirement.md`、`docs/architecture/adr/README`、`docs/architecture/tech-architecture-design-v3.md` | — | 写代码 / 改 state.json | `templates/phase/02-tech-design.md` + ADR 草案 | 引用 ≥1 ADR + FR 一一映射 |
| **REVIEW_ARCH** | `templates/phase/02-tech-design.md` | — | 写代码 / 改 state.json | `templates/review/review-arch.md` | 重度审查 + 架构变更已澄清 |
| **ATDD** | `templates/phase/02-tech-design.md`、`docs/architecture/TDS/`* | `docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html` | 写代码 / 改 state.json | `templates/phase/04-atdd.md` | ≥1 Gherkin 三态覆盖 |
| **REVIEW_ATDD** | `templates/phase/04-atdd.md` | — | 写代码 / 改 state.json | `templates/review/review-atdd.md` | alignment_check: PASS |
| **TDS** | `templates/phase/02-tech-design.md`、`templates/phase/04-atdd.md` | — | 写代码 / 改 state.json | `templates/phase/04-tds.md` | tds_modules 已定义 |
| **REVIEW_TDS** | `templates/phase/04-tds.md` | — | 写代码 / 改 state.json | `templates/review/review-tds.md` | alignment_check: PASS |
| **PLAN** | `templates/phase/04-tds.md`、`templates/phase/04-atdd.md` | `cursor-dev-spec.md`（前端 FR 时） | 写代码 / 改 state.json | `templates/phase/05-plan.md` | 实施计划含时间估算 |
| **REVIEW_PLAN** | `templates/phase/05-plan.md` | — | 写代码 / 改 state.json | `templates/review/review-plan.md` | alignment_check: PASS |
| **PRE_MORTEM** | `templates/phase/0[1-5]-*.md` | — | 写代码 / 改 state.json | `templates/phase/03-pre-mortem.md`（orchestrator 合成） | 3 评审签字 |
| **CODE** | `templates/phase/05-plan.md`、`coding-standards`、`ad-tdd` Skill | `cursor-dev-spec.md`（前端 token） + `cursor-api-contract.md`（API 调用） | 读 REQUIREMENT 原文 / 改 state.json | `templates/phase/06-code.md` | L0-L6 门禁全 PASS |
| **DEPLOY** | `templates/phase/06-code.md` | — | 读 REQUIREMENT 原文 | `templates/phase/09-deploy.md` | 部署成功/跳过 |
| **VERIFY** | `templates/phase/06-code.md`、`EXECUTORS.md`（verifier） | — | 读 REQUIREMENT 原文 | `templates/phase/07-verify.md` | L0-L6 全 PASS |
| **SECURITY_TEST** | `templates/phase/06-code.md`、`coding-standards/RULES.md` | — | 写代码 | `templates/phase/08-security-test.md` | bandit 无 S/F |
| **REGRESSION** | `templates/phase/09-deploy.md` | — | 读 REQUIREMENT 原文 | `templates/phase/10-regression.md` | 回归测试全 PASS |
| **SIGN_OFF** | `templates/phase/10-regression.md` | — | 读 REQUIREMENT 原文 | `templates/phase/11-signoff.md` | PR-Gate 7 项全 PASS |
| **DATA_REPLAY** | `templates/phase/11-signoff.md`、`docs/PRD/`* | — | — | `templates/phase/12-data-replay.md` | `replay_session_id` 已生成 |
| **INCIDENT_RESPONSE** | `templates/phase/11-signoff.md`、`templates/phase/09-deploy.md` | — | 跳过根因 | `templates/phase/13-incident-response.md` | stakeholder 已通知 |
| **OPS_LOOP** | `templates/phase/13-*.md`、`templates/phase/11-signoff.md` | — | 跳过灰度 | `templates/phase/14-ops-loop.md` | 统计显著性达成 |
| **SKILL_UPDATE** | `templates/phase/14-*.md`、`harness/lessons/`、`harness-autolearn` | — | 强制晋升 | `templates/phase/15-skill-update.md` | lesson 沉淀 |
| **INTERRUPT_REVIEW** | `harness-state.json`、`templates/<interrupted_phase>.md` | — | 修改被中断 evidence | `templates/phase/16-interrupt-review.md` | 决策已执行 |
| **ARCH_CLARIFICATION** | 触发它的 Review evidence | — | 不升级用户 | `templates/arch-clarification.md` | user_approved: true |


## 二、与其他文件的边界

- 本文件**只**列出阶段规则；具体模板路径见 `harness/evidence/templates/`
- 状态机定义见 `harness/workflow-v3.yaml`（**V3 唯一真源**）
- 兼容旧版：`harness/workflow-v2.yaml`（V2，过渡期只读）
- 角色协议见 `agents/harness/{DISPATCHER,ORCHESTRATOR,REVIEWERS,EXECUTORS}.md`
- evidence schema 见 `harness/evidence/README.md`（V3 模板结构）

## 三、红线兜底

- `.cursor/rules/project-prohibitions.mdc` R-2（agents/ 禁止业务规则）/ R-5（禁止 shell 跳级）
- `.cursor/rules/coding-standards.mdc` alwaysApply 编码规范
- `.cursor/rules/l0-l6-gates.mdc` L0-L6 质量门禁真源
