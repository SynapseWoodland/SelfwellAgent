---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-reviewers
---

# REVIEWERS — 5 评审角色协议（V2：16 phase）

> **V2 更新**：新增 SECURITY_TEST（独立安全评审）和 INCIDENT_RESPONSE（故障响应）。
> 必签 3 + 触发式 2。3 必签 = `requirement-analyst` / `tech-architect` / `quality-guardian`；2 触发式 = `security-reviewer`（PII/LLM/对外 API 时）/ `devops-reviewer`（CI/部署/迁移时）。
> 触发规则见 `docs/harness/context/phase-checklist.md` §二。
> **不重复** ORCHESTRATOR 的合成协议；不重复 harness-evidence Skill 的 schema（见 `docs/harness/evidence/README.md`）。

## 一、5 评审角色总览

| # | 角色 ID | 视角 | 触发 phase | 写 evidence |
|---|---------|------|-----------|-------------|
| 1 | `requirement-analyst` | 业务 | `PRD` / `PRE_MORTEM` / `DATA_REPLAY` | `evidence/01-requirement.md` / `evidence/12-data-replay.md` |
| 2 | `tech-architect` | 技术 | `ARCH_DESIGN` / `PRE_MORTEM` | `evidence/02-tech-design.md` |
| 3 | `quality-guardian` | 质量 | `ATDD` / `PRE_MORTEM` / `SKILL_UPDATE` / `INTERRUPT_REVIEW` | `evidence/04-atdd.md` / `evidence/15-skill-update.md` / `evidence/16-interrupt-review.md` |
| 4 | `security-reviewer` | 安全 | `PRE_MORTEM`（**触发式**）/ `SECURITY_TEST` | `evidence/03b-security.md` / `evidence/08-security-test.md` |
| 5 | `devops-reviewer` | 部署 | `PRE_MORTEM`（**触发式**）/ `INCIDENT_RESPONSE` | `evidence/03c-devops.md` / `evidence/13-incident-response.md` |

> 阶段名严格对齐 `docs/harness/workflow-v2.yaml`。

## 二、各角色协议

### 2.1 requirement-analyst（业务）

- **Read**：`docs/PRD/*.md`、`docs/scenarios/*.md`、`docs/spec/SPEC-A0-MASTER-IA.md`
- **Write**：`evidence/01-requirement.md`、`evidence/12-data-replay.md`（DATA_REPLAY）
- **禁用**：业务代码 / Skill 内容
- **5 问**：FR 编号完整？三态覆盖？跨模块耦合？验收可测？新角色/权限？

### 2.2 tech-architect（技术）

- **Read**：`PRD`、`ADR-*`、`TDS-*`、`docs/architecture/tech-architecture-design-v3.md`
- **Write**：`evidence/02-tech-design.md`（含 ADR draft）
- **禁用**：业务代码实现
- **5 问**：与现有 ADR 一致？V3 边界？新依赖（R-1）？新债？目录树对齐？

### 2.3 quality-guardian（质量）

- **Read**：`TDS-*`、`ATDD`、`coding-standards.mdc`、`ad-tdd/SKILL.md`
- **Write**：`evidence/04-atdd.md`、`evidence/15-skill-update.md`、`evidence/16-interrupt-review.md`
**门禁引用**（不写死）：整体 ≥ 60% / rules ≥ 90% / agents+middleware ≥ 80% / tools ≥ 70%（真源 `.cursor/rules/l0-l6-gates.mdc` §一 L6 + §二）
- **禁用**：业务代码、修改 Skill
- **5 问**：ATDD 三态？字段映射 openapi？覆盖率可达？跨 FR 回归？新增 Golden Set？

### 2.4 security-reviewer（安全，**触发式** + **独立阶段**）

- **触发**：涉及 PII / LLM / 对外 API / 鉴权
- **Read**：`coding-standards/RULES.md`、`error-codes.md`、`openapi.yaml`
- **Run**：`bandit -r backend/app`（仅读）
- **Write**：`evidence/03b-security.md`（PRE_MORTEM 触发式）、`evidence/08-security-test.md`（SECURITY_TEST 独立）
- **禁用**：业务代码、修改 RULES.md
- **5 问**：PII 字段？参数化绑定？合规四层（V3 §5.1）？日志 PII 黑名单？新密钥入口？

### 2.5 devops-reviewer（部署，**触发式** + **INCIDENT_RESPONSE**）

- **触发**：涉及 CI / 部署 / 数据库迁移 / 生产故障
- **Read**：`.github/workflows/*.yml`、`docker-compose.yaml`、`db/init/*.sql`、`alembic/`
- **Write**：`evidence/03c-devops.md`（PRE_MORTEM 触发式）、`evidence/13-incident-response.md`（INCIDENT_RESPONSE）
- **禁用**：业务 feature 代码
- **5 问**：CI 触发 backend-ci？迁移有 downgrade？预发覆盖？外部依赖额度？上线需人工确认？

## 三、evidence 文件四段式

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

## 四、硬禁止清单（R-2 + 角色边界）

| # | 禁止 | 兜底 |
|---|------|------|
| 1 | 写业务代码 | reviewer 只写 evidence |
| 2 | 跨视角合并 | 合并由 orchestrator 负责 |
| 3 | 直接修改 ADR / TDS / Skill | reviewer 只提"变更建议" |
| 4 | 越界 Read | 仅 Read §二"可用工具"清单 |
| 5 | evidence 硬编码业务阈值（`if score > 0.8`） | grep `if.*score.*>` 必须无命中 |

## 五、退出条件

1. 写 evidence + 标 ✅/⚠️/🔴
2. 缺段 → 自检失败重写
3. 输入缺失 → 返回 dispatcher 补出 phase

## 六、与其他协议文件边界

| Skill | 关系 |
|-------|------|
| `coding-standards.mdc` | **被引用**（quality 评审阈值以 coding-standards 为真源） |
| `pr-gate/SKILL.md` | **被引用**（PRE_MORTEM / SIGN_OFF 末尾跑 pr-gate 7 项） |
| `ad-tdd/SKILL.md` | **被引用**（tech-architect 评审 TDS 时参考） |
| `frontend-standards/SKILL.md` | **被引用**（前端任务评审角度叠加） |
| `golden-set/SKILL.md` | **不调用**（REGRESSION 阶段才触发） |

## 七、参考

- 上游：`agents/harness/DISPATCHER.md`（按 phase 路由到 reviewer）
- 下游：`agents/harness/ORCHESTRATOR.md`（合成 5 reviewer 产物）
- 模板：`docs/harness/templates/pre-mortem.md` / `synthesis.md`
- evidence schema：`docs/harness/evidence/README.md`（V2 8 字段）
- workflow-v2.yaml：`docs/harness/workflow-v2.yaml`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2
