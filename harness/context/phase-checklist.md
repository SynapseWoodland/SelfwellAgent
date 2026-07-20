---

## name: harness-context-phase-checklist

description: >
  Harness 16 phase context 合并为 5 列表格（V2 含 6 个新 phase）。
  当 dispatcher 路由到任一 phase 时由主会话按需 Read。
disable-model-invocation: true

# Phase Checklist（V2：16 phase）

> **V2 更新**：6 个新 phase（SECURITY_TEST / INCIDENT_RESPONSE / OPS_LOOP / SKILL_UPDATE / DATA_REPLAY / INTERRUPT_REVIEW）已加入速查表。
> 阶段切换时 dispatcher **不重新加载**本文件，仅更新 `state.json.current_phase`。
> V2 新 phase 的详细 context 见 `harness/context/NN-<phase>.md`。

## 一、16 阶段 × 6 字段速查表

> **必读文档来源说明（按 Harness 架构师视角分层）**：
>
> ### A. 核心架构文档（必读）
>
> | 文档 | 说明 | 来源 |
> |------|------|------|
> | `docs/architecture/tech-architecture-design-v3.md` | **V3 技术架构真源** | 唯一真源 |
> | `docs/architecture/SELFWELL-MVP-SDS.md` | **MVP 系统设计规格说明书** | 核心设计 |
> | `docs/architecture/4plus1-view-model.md` | **4+1 视图模型** | 架构全景 |
> | `docs/architecture/api.yaml` | **OpenAPI 接口规格** | API 真源 |
> | `docs/architecture/error-codes.md` | **错误码规范** | 错误码真源 |
> | `docs/architecture/sse-events.md` | **SSE 事件契约** | 流式事件真源 |
> | `docs/architecture/ddd-bounded-context.md` | **DDD 限界上下文** | 架构边界真源 |
>
> ### B. 决策记录（ADR）
>
> | 文档 | 说明 | 来源 |
> |------|------|------|
> | `docs/architecture/adr/README.md` | **ADR 索引** | 所有决策记录入口 |
> | `docs/architecture/adr/0001-tech-stack.md` | 技术栈决策 | ADR-0001 |
> | `docs/architecture/adr/0003-llm-primary-fallback.md` | LLM 主备决策 | ADR-0003 |
> | `docs/architecture/adr/0015-persona-contract.md` | Persona 契约 | ADR-0015 |
> | `docs/architecture/adr/0016-feedback-unified.md` | Feedback 统一 | ADR-0016 |
> | `docs/architecture/adr/0019-async-sse-pipeline.md` | 异步 SSE 管道 | ADR-0019 |
> | 其他 ADR | 见 `adr/README.md` | ADR-0002~ADR-0018 |
>
> ### C. 技术设计规格（TDS）
>
> | 文档 | 说明 | 来源 |
> |------|------|------|
> | `docs/architecture/TDS/TDS-M1-wechat-login.md` | 微信登录 | M1 |
> | `docs/architecture/TDS/TDS-M2-multimodal-diagnosis.md` | 多模态诊断 | M2 |
> | `docs/architecture/TDS/TDS-M3-21day-plan.md` | 21 天计划 | M3 |
> | `docs/architecture/TDS/TDS-M4-checkin-loop.md` | 打卡循环 | M4 |
> | `docs/architecture/TDS/TDS-M5-persona-chat.md` | Persona 聊天 | M5 |
> | `docs/architecture/TDS/TDS-M6-plaza-community.md` | 广场社区 | M6 |
> | `docs/architecture/TDS/TDS-M7-feedback.md` | Feedback 机制 | M7 |
> | `docs/architecture/TDS/TDS-M8-recall.md` | Recall 机制 | M8 |
> | 其他 TDS | 见 `TDS/` 目录 | M9~M14 |
>
> ### D. 数据架构
>
> | 文档 | 说明 | 来源 |
> |------|------|------|
> | `docs/architecture/data/data-architecture.md` | 数据架构 | 核心 |
> | `docs/architecture/data/forbidden-words.md` | 禁用词 | 合规 |
> | `docs/architecture/data/medical-reject-words.yaml` | 医疗拒绝词 | 合规 |
> | `docs/architecture/data/mental-health-crisis-words.yaml` | 心理健康危机词 | 合规 |
> | `docs/architecture/data/recall-forbidden-words.yaml` | Recall 禁用词 | 合规 |
> | `docs/architecture/data/seed-data-plan.md` | 种子数据计划 | 数据初始化 |
>
> ### E. 业务需求与合规
>
> | 文档 | 说明 | 来源 |
> |------|------|------|
> | `docs/PRD/`* | 业务需求文档目录 | PRD 原文 |
> | `docs/requirements/SELFWELL-MVP-SRS.md` | 系统需求规格说明书（SRS） | SRS 真源 |
> | `docs/compliance/README.md` | 合规框架 | 合规索引 |
> | `docs/compliance/minors.md` | 未成年人保护 | 合规 |
> | `docs/compliance/privacy-policy.md` | 隐私政策 | 合规 |
> | `docs/compliance/terms-of-service.md` | 服务条款 | 合规 |
> | `docs/compliance/coppa.md` | COPPA 合规 | 合规 |
> | `docs/compliance/gdpr.md` | GDPR 合规 | 合规 |
> | `docs/compliance/content-policy.md` | 内容政策 | 合规 |
> | `docs/compliance/operator-handbook.md` | 运营手册 | 合规 |
>
> ### F. 前端设计
>
> | 文档 | 说明 | 来源 |
> |------|------|------|
> | `docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html` | **前端原型真源**（唯一） | V2 原型 |
> | `docs/frontend-design/figma-pixso-spec/design-tokens/tokens.json` | 设计 Token | 样式真源 |
> | `docs/frontend-design/design-spec.md` | 设计规范 | 前端规范 |
> | `docs/frontend-design/forbidden-words.md` | 前端禁用词 | 合规 |
>
> ### G. 其他重要文档
>
> | 文档 | 说明 | 来源 |
> |------|------|------|
> | `workflow-v2.yaml` | Harness V2 工作流真源 | 流水线定义 |
> | `coding-standards.mdc` | Python 编码规范 | alwaysApply |
> | `l0-l6-gates.mdc` | L0-L6 质量门禁 | alwaysApply |
> | `project-prohibitions.mdc` | 工程红线 | alwaysApply |
>
> ### H. Evidence 文档来源字段说明（V2 新增）
>
> **核心原则**：evidence 是变更追踪，不是完整文档。记录本轮改过的文档，改什么记什么，不改的不记。
>
> | Evidence 文件 | 文档来源字段 | 说明 |
> |-------------|-------------|------|
> | `evidence/01-requirement.md` | `source_doc` / `created_from_scratch` | 引用已有 SRS 或从0创建 |
> | `evidence/02-tech-design.md` | `source_sds` / `source_tds_modules` / `created_tds_modules` | 引用已有 SDS/TDS |
> | `evidence/03-atdd.md` | `tds_ref` / `atdd_docs` | 关联 TDS + ATDD 列表 |
>
> **docs/architecture/ 下所有文档类型**：
>
> | 文档类型 | 是否记录 | 记录位置 |
> |---------|---------|---------|
> | SDS | ✅ 必记 | `source_sds` |
> | TDS | ✅ 改了就记 | `source_tds_modules` / `created_tds_modules` |
> | ADR | ✅ 改了就记 | `new_adrs` |
> | api.yaml / error-codes / sse-events 等 | ✅ 改了就记 | `involved_architecture` |
> | data/*.yaml | ✅ 改了就记 | `involved_data` |


| 阶段                        | 必读（核心文档）                                                                                          | 合规/前端补充                                                                                                                                                            | 禁用                                    | 必产物                                            | 退出                                     |
| ------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------- | ---------------------------------------------- | -------------------------------------- |
| **REQUIREMENT** | `docs/PRD/*`、`workflow-v2.yaml` | — | 写代码 / 改 state.json / 读其他 context | `evidence/01-requirement.md` + state.json 更新 | FR 编号全覆盖 + 每个 FR ≥1 场景 |
| **ARCH_DESIGN**           | `evidence/01-requirement.md`、`docs/architecture/adr/README`、`docs/architecture/tech-architecture-design-v3.md` | `docs/compliance/privacy-policy.md`、`docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html`、`docs/architecture/SELFWELL-MVP-SDS.md` | 写代码 / 改 state.json / 读 REQUIREMENT 原文 | TDS 骨架 + `evidence/02-tech-design.md` + ADR 草案 | 引用 ≥1 ADR + FR 一一映射 + frontmatter 8 字段 |
| **PRE_MORTEM**            | `evidence/0[1-2]-*.md`、`docs/architecture/TDS/`*、3 份模板                                        | —                                                                                                                                                                  | 写代码 / 改 state.json / 跨 phase evidence | `evidence/03-pre-mortem.md`（3 必签 + 2 触发签字）     | 3 评审签字 + orchestrator 合成               |
| **ATDD**                  | `evidence/01-04*.md`、`docs/architecture/TDS/`*、3 份模板                                             | `docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html`                                                                                        | 写代码 / 改 state.json                    | `evidence/04-atdd.md`（≥1 Gherkin 三态覆盖）         | ATDD 字段映射 openapi；产出用于 CODE 阶段 TDD       |
| **PLAN**                  | `evidence/04-atdd.md`、`docs/architecture/TDS/`*、`coding-standards`                                    | —                                                                                                                                                                  | 写代码 / 改 state.json                    | `evidence/05-plan.md`                          | 实施计划含时间估算                              |
| **CODE**                  | `evidence/05-plan.md`、`docs/architecture/TDS/`*、`coding-standards`、`ad-tdd` Skill                              | `docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html`、`docs/architecture/api.yaml`                                                            | 读 REQUIREMENT 原文 / 改 state.json               | `evidence/06-code.md`                          | L0-L6 门禁全 PASS；TDD Unit Test PASS          |
| **VERIFY**                | `evidence/06-code.md`、`docs/architecture/TDS/`*、`EXECUTORS.md`（verifier）                                             | —                                                                                                                                                                  | 读 REQUIREMENT 原文 / 改 state.json               | `evidence/07-verify.md`                        | integration + API-E2E + smoke + UI-E2E PASS   |
| **SECURITY_TEST**（V2）     | `evidence/06-*.md`、`evidence/07-verify.md`、`coding-standards/RULES.md`                               | `docs/compliance/README.md`、`docs/architecture/data/forbidden-words.md`                                                                                          | 写代码 / 读 REQUIREMENT 原文                        | `evidence/08-security-test.md`                 | bandit 无 S/F + PII 合规                  |
| **DEPLOY**                | `evidence/07-verify.md`、`evidence/08-*.md`、`docs/deployment/README.md`                              | —                                                                                                                                                                  | 读 REQUIREMENT 原文 / 改 state.json               | `evidence/09-deploy.md`                        | 部署验证通过                                 |
| **REGRESSION**            | `evidence/09-deploy.md`                                                                           | —                                                                                                                                                                  | 读 REQUIREMENT 原文 / 改 state.json               | `evidence/10-regression.md`                    | 回归测试全 PASS                             |
| **SIGN_OFF**              | `evidence/10-*.md`、pr-gate                                                                         | —                                                                                                                                                                  | 读 REQUIREMENT 原文 / 改 state.json               | `evidence/11-signoff.md`（5 评审签字）               | PR-Gate 7 项全 PASS                      |
| **DATA_REPLAY**（V2）       | `evidence/11-signoff.md`、`docs/PRD/`*                                                               | —                                                                                                                                                                  | 忽略 REQUIREMENT 偏差                             | `evidence/12-data-replay.md`                   | 偏差已记录 + `replay_session_id` 已生成        |
| **INCIDENT_RESPONSE**（V2） | `evidence/11-signoff.md`、`evidence/09-deploy.md`                                                     | `docs/compliance/README.md`、`docs/metrics/alerting.md`                                                                                                          | 跳过根因 / 未通知 stakeholder                | `evidence/13-incident-response.md`             | 冷静期已过 + stakeholder 已通知                |
| **OPS_LOOP**（V2）          | `evidence/13-*.md`、`evidence/11-signoff.md`                                                         | —                                                                                                                                                                  | 跳过灰度 / 修改 A/B                         | `evidence/14-ops-loop.md`                      | 统计显著性达成                                |
| **SKILL_UPDATE**（V2）      | `evidence/14-*.md`、`harness/lessons/`、`harness-autolearn`                                           | —                                                                                                                                                                  | 强制晋升                                  | `evidence/15-skill-update.md`                  | lesson 沉淀 + 晋升判断已记录                    |
| **INTERRUPT_REVIEW**（V2）  | `harness-state.json`、`evidence/<interrupted_phase>.md`、`docs/architecture/4plus1-view-model.md`           | —                                                                                                                                                                  | 修改被中断 evidence                        | `evidence/16-interrupt-review.md`              | 决策已执行（继续/推迟/升级）                        |


> V2 新 phase（SECURITY_TEST / DATA_REPLAY / INCIDENT_RESPONSE / OPS_LOOP / SKILL_UPDATE / INTERRUPT_REVIEW）的详细 context 见 `harness/context/NN-<phase>.md`。

## 二、Pre-Mortem 签字触发式扩展规则


| 触发条件                          | 必追加签字                  |
| ----------------------------- | ---------------------- |
| 涉及 PII / LLM 调用 / 对外 API / 密钥 | security-reviewer      |
| 涉及 CI 配置 / 部署 / 数据库迁移 / 基础设施  | devops-reviewer        |
| 涉及 覆盖率 / 门禁 / ATDD            | quality-guardian（必签之一） |


未触发角色显式填"无意见 / 不适用"。

## 三、与其他文件的边界

- 本文件**只**列出阶段规则；具体模板路径见 `harness/templates/`
- 状态机定义见 `harness/workflow-v2.yaml`（V2 唯一真源）
- 兼容旧版：`harness/workflow.yaml`（V1.6，迁移期只读）
- 角色协议见 `agents/harness/{DISPATCHER,ORCHESTRATOR,REVIEWERS,EXECUTORS}.md`
- evidence schema 见 `harness/evidence/README.md`（V2 8 字段）

## 四、参考

### 4.1 核心文档索引

| 类别 | 文档 | 说明 |
|------|------|------|
| **架构真源** | `docs/architecture/tech-architecture-design-v3.md` | V3 技术架构唯一真源 |
| **架构全景** | `docs/architecture/4plus1-view-model.md` | 4+1 视图模型 |
| **API 规格** | `docs/architecture/api.yaml` | OpenAPI 接口真源 |
| **错误码** | `docs/architecture/error-codes.md` | 错误码规范 |
| **SSE 事件** | `docs/architecture/sse-events.md` | 流式事件契约 |
| **DDD 边界** | `docs/architecture/ddd-bounded-context.md` | 限界上下文真源 |
| **SDS** | `docs/architecture/SELFWELL-MVP-SDS.md` | MVP 系统设计规格 |
| **SRS** | `docs/requirements/SELFWELL-MVP-SRS.md` | 系统需求规格 |
| **原型** | `docs/frontend-design/figma-pixso-spec/pages-v2/00-phone-prototype-v1.html` | 前端原型真源（唯一） |
| **合规** | `docs/compliance/README.md` | 合规框架索引 |
| **数据** | `docs/architecture/data/data-architecture.md` | 数据架构 |
| **ADR** | `docs/architecture/adr/README.md` | ADR 决策索引 |

### 4.2 Harness 内部文档

| 文档 | 说明 |
|------|------|
| `harness/workflow-v2.yaml` | V2 工作流唯一真源 |
| `harness/evidence/README.md` | V2 evidence 8 字段 |
| `harness/context/NN-<phase>.md` | V2 新 phase 详细 context |
| `harness/templates/` | 阶段模板路径 |
| `harness/lessons/` | lesson 沉淀目录 |

### 4.3 红线兜底

- `.cursor/rules/project-prohibitions.mdc` R-2（agents/ 禁止业务规则）/ R-5（禁止 shell 跳级）
- `.cursor/rules/coding-standards.mdc` alwaysApply 编码规范
- `.cursor/rules/l0-l6-gates.mdc` L0-L6 质量门禁真源

