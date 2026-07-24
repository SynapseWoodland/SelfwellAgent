---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-reviewers
---

# REVIEWERS — 6 评审角色协议（V3：22 phase + 5 Review）

> **V3 更新**：新增 `REVIEW_SRS` / `REVIEW_ARCH` / `REVIEW_ATDD` / `REVIEW_TDS` / `REVIEW_PLAN`（5 个 Review 节点）+ `TDS` + `ARCH_CLARIFICATION`。
> 必签 3 + 触发式 2。3 必签 = `requirement-analyst` / `tech-architect` / `quality-guardian`；2 触发式 = `security-reviewer`（PII/LLM/对外 API 时）/ `devops-reviewer`（CI/部署/迁移时）。
> Review 节点负责文档质量审查，最多打回 3 次，超过触发 `ARCH_CLARIFICATION`。
> 触发规则见 `harness/context/phase-checklist.md` §二。
> **不重复** ORCHESTRATOR 的合成协议；不重复 harness-evidence Skill 的 schema（见 `harness/evidence/README.md`）。

## 一、6 评审角色总览

| # | 角色 ID | 视角 | 触发 phase | 写 evidence |
|---|---------|------|-----------|-------------|
| 1 | `requirement-analyst` | 业务 | `REQUIREMENT` / `REVIEW_SRS` / `PRE_MORTEM` / `DATA_REPLAY` | `templates/phase/01-requirement.md` / `templates/review/review-srs.md` |
| 2 | `tech-architect` | 技术 | `ARCH_DESIGN` / `REVIEW_ARCH` / `TDS` / `REVIEW_TDS` / `ARCH_CLARIFICATION` | `templates/phase/02-tech-design.md` / `templates/review/review-arch.md` / `templates/phase/04-tds.md` / `templates/review/review-tds.md` |
| 3 | `quality-guardian` | 质量 | `ATDD` / `REVIEW_ATDD` / `PRE_MORTEM` / `SKILL_UPDATE` / `INTERRUPT_REVIEW` | `templates/phase/04-atdd.md` / `templates/review/review-atdd.md` |
| 4 | `security-reviewer` | 安全 | `PRE_MORTEM`（**触发式**）/ `SECURITY_TEST` | `templates/phase/08-security-test.md` |
| 5 | `devops-reviewer` | 部署 | `PRE_MORTEM`（**触发式**）/ `INCIDENT_RESPONSE` | `templates/phase/13-incident-response.md` |
| 6 | `plan-generator` | 实施 | `PLAN` / `REVIEW_PLAN` | `templates/phase/05-plan.md` / `templates/review/review-plan.md` |

> V3 新增 `REVIEW_SRS` / `REVIEW_ARCH` / `REVIEW_ATDD` / `REVIEW_TDS` / `REVIEW_PLAN` / `TDS` / `ARCH_CLARIFICATION` phase。
> 阶段名严格对齐 `harness/workflow-v3.yaml`。

## 二、各角色协议

### 2.1 requirement-analyst（业务）

- **Read**：`docs/PRD/*.md`、`docs/scenarios/*.md`、`docs/spec/SPEC-A0-MASTER-IA.md`
- **Write**：`templates/phase/01-requirement.md`、`templates/phase/13-data-replay.md`（DATA_REPLAY）
- **禁用**：业务代码 / Skill 内容
- **5 问**：FR 编号完整？三态覆盖？跨模块耦合？验收可测？新角色/权限？

### 2.2 tech-architect（技术）

- **Read**：`PRD`、`ADR-*`、`TDS-*`、`docs/architecture/tech-architecture-design-v3.md`
- **Write**：`templates/phase/02-tech-design.md`（含 ADR draft）、`templates/phase/04-tds.md`（TDS 阶段）
- **禁用**：业务代码实现
- **5 问**：与现有 ADR 一致？V3 边界？新依赖（R-1）？新债？目录树对齐？

### 2.3 quality-guardian（质量）

- **Read**：`TDS-*`、`ATDD`、`coding-standards.mdc`、`ad-tdd/SKILL.md`
- **Write**：`templates/phase/04-atdd.md`、`templates/phase/15-skill-update.md`、`templates/phase/17-interrupt-review.md`
- **门禁引用**（不写死）：整体 ≥ 60% / rules ≥ 90% / agents+middleware ≥ 80% / tools ≥ 70%（真源 `.cursor/rules/l0-l6-gates.mdc` §一 L6 + §二）
- **禁用**：业务代码、修改 Skill
- **5 问**：ATDD 三态？字段映射 openapi？覆盖率可达？跨 FR 回归？新增 Golden Set？

### 2.4 security-reviewer（安全，**触发式** + **独立阶段**）

- **触发**：涉及 PII / LLM / 对外 API / 鉴权
- **Read**：`coding-standards/RULES.md`、`error-codes.md`、`openapi.yaml`
- **Run**：`bandit -r backend/app`（仅读）
- **Write**：`templates/phase/08-security-test.md`（SECURITY_TEST 独立）
- **禁用**：业务代码、修改 RULES.md
- **5 问**：PII 字段？参数化绑定？合规四层（V3 §5.1）？日志 PII 黑名单？新密钥入口？

### 2.5 devops-reviewer（部署，**触发式** + **INCIDENT_RESPONSE**）

- **触发**：涉及 CI / 部署 / 数据库迁移 / 生产故障
- **Read**：`.github/workflows/*.yml`、`docker-compose.yaml`、`db/init/*.sql`、`alembic/`
- **Write**：`templates/phase/13-incident-response.md`（INCIDENT_RESPONSE）
- **禁用**：业务 feature 代码
- **5 问**：CI 触发 backend-ci？迁移有 downgrade？预发覆盖？外部依赖额度？上线需人工确认？

### 2.6 plan-generator（实施）

- **Read**：TDS、ATDD、ARCH_DESIGN 文档
- **Write**：`templates/phase/05-plan.md`（PLAN）、`templates/review/review-plan.md`（REVIEW_PLAN）
- **禁用**：业务代码实现
- **5 问**：任务分解粒度？依赖关系清晰？DDD 规范符合？实施可行？风险识别？

## 三、Review 节点职责（V3 新增）

| Review 节点 | 负责角色 | 审查深度 | 最多打回次数 |
|-------------|----------|----------|--------------|
| `REVIEW_SRS` | requirement-analyst | medium | 3 |
| `REVIEW_ARCH` | tech-architect | **heavy** | 3 |
| `REVIEW_ATDD` | quality-guardian | light | 3 |
| `REVIEW_TDS` | tech-architect | medium | 3 |
| `REVIEW_PLAN` | plan-generator | light | 3 |

### 3.1 Review 审查深度说明

| 深度 | 说明 | 适用场景 |
|------|------|----------|
| **light** | 场景格式、Given-When-Then、覆盖度 | REVIEW_ATDD, REVIEW_PLAN |
| **medium** | 加上唯一真源检查、业务/技术对齐 | REVIEW_SRS, REVIEW_TDS |
| **heavy** | 加上架构方案选择、与用户澄清 | REVIEW_ARCH |

### 3.2 3次打回机制

1. Review FAIL → 打回上一 phase 修改 → `rejection_count + 1`
2. `rejection_count >= 3` → 触发 `ARCH_CLARIFICATION`
3. `ARCH_CLARIFICATION` 产出方案选项 → 用户选择 → 继续流程

## 四、evidence 文件四段式

```markdown
# <角色> 评审报告 — <phase>

## 一、视角结论（≤ 5 行）

## 二、评审 5 问清单（必答）
1. <问 1> — ✅ / ⚠️ / 🔴 —— 依据：...

## 三、ADR / TDS / Skill 变更建议
| 类型 | 建议 | 阻塞 phase |
| 新增 ADR-XXXX | ... | ✅ / ⚠️ |

## 四、签字 / 退回
- ✅ 通过 / ⚠️ 有条件通过 / 🔴 退回
```

> 状态语义由 ORCHESTRATOR 解读，本文件不展开。

## 五、硬禁止清单（R-2 + 角色边界）

| # | 禁止 | 兜底 |
|---|------|------|
| 1 | 写业务代码 | reviewer 只写 evidence |
| 2 | 跨视角合并 | 合并由 orchestrator 负责 |
| 3 | 直接修改 ADR / TDS / Skill | reviewer 只提"变更建议" |
| 4 | 越界 Read | 仅 Read §二"可用工具"清单 |
| 5 | evidence 硬编码业务阈值（`if score > 0.8`） | grep `if.*score.*>` 必须无命中 |
| 6 | Review 节点超过 3 次打回 | 触发 ARCH_CLARIFICATION |

## 六、退出条件

1. 写 evidence + 标 ✅/⚠️/🔴
2. 缺段 → 自检失败重写
3. 输入缺失 → 返回 dispatcher 补出 phase

## 七、与其他协议文件边界

| Skill | 关系 |
|-------|------|
| `coding-standards.mdc` | **被引用**（quality 评审阈值以 coding-standards 为真源） |
| `pr-gate/SKILL.md` | **被引用**（PRE_MORTEM / SIGN_OFF 末尾跑 pr-gate 7 项） |
| `ad-tdd/SKILL.md` | **被引用**（tech-architect 评审 TDS 时参考） |
| `frontend-standards/SKILL.md` | **被引用**（前端任务评审角度叠加） |
| `golden-set/SKILL.md` | **不调用**（REGRESSION 阶段才触发） |

## 八、参考

- 上游：`agents/harness/DISPATCHER.md`（按 phase 路由到 reviewer）
- 下游：`agents/harness/ORCHESTRATOR.md`（合成 5 reviewer 产物）
- 模板：`harness/evidence/templates/phase/` / `harness/evidence/templates/review/`
- evidence schema：`harness/evidence/README.md`（V3 结构）
- workflow-v3.yaml：`harness/workflow-v3.yaml`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2
