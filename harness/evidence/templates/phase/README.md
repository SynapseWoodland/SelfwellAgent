# Phase Evidence 模板

此目录包含所有 Phase 的 evidence 模板。

## 命名规范

格式：`NN-<phase-suffix>.md`

| 文件名 | 对应 phase | 作者角色 | V3 |
|--------|------------|----------|-----|
| `01-requirement.md` | REQUIREMENT | requirement-analyst | ✅ |
| `02-tech-design.md` | ARCH_DESIGN | tech-architect | ✅ |
| `03-pre-mortem.md` | PRE_MORTEM | orchestrator | ✅ |
| `04-atdd.md` | ATDD | quality-guardian | ✅ |
| `04-tds.md` | TDS | tech-architect | **V3 新增** |
| `05-plan.md` | PLAN | plan-generator | ✅ |
| `06-code.md` | CODE | developer | ✅ |
| `07-verify.md` | VERIFY | verifier | ✅ |
| `08-security-test.md` | SECURITY_TEST | security-reviewer | ✅ |
| `09-deploy.md` | DEPLOY | deployer | ✅ |
| `10-regression.md` | REGRESSION | tester | ✅ |
| `11-signoff.md` | SIGN_OFF | orchestrator | ✅ |
| `12-data-replay.md` | DATA_REPLAY | requirement-analyst | ✅ |
| `13-incident-response.md` | INCIDENT_RESPONSE | deployer | ✅ |
| `14-ops-loop.md` | OPS_LOOP | tester | ✅ |
| `15-skill-update.md` | SKILL_UPDATE | quality-guardian | ✅ |
| `16-interrupt-review.md` | INTERRUPT_REVIEW | quality-guardian | ✅ |

## 使用说明

1. 每次运行新 phase 时，从对应模板复制到 `runs/<run_id>/` 目录
2. 填充模板内容
3. 在 `harness/state/harness-state.json` 中记录 evidence 路径
