---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-executors
---
# EXECUTORS — 5 执行角色协议（A 档精简版）

> **A 档精简**：原 8 章 → 6 章；合并 §三 Skill 调用矩阵进 §二各角色；删 §八 参考。
> 5 个 executor 对应 `PLAN / CODE / VERIFY / DEPLOY / REGRESSION`；**只调用既有 Skill**，不重复造轮子；**所有业务代码 / 业务规则落 `backend/app/`、`apps/`、`rules/`**（R-2 红线）。

## 一、5 执行角色总览

| # | 角色 ID | phase | 主用 Skill | evidence |
|---|---------|-------|-----------|----------|
| 1 | `plan-generator` | `PLAN` | `ad-tdd` Phase 1 | `05-plan.md` + `TDS-<id>.md` 实施计划 |
| 2 | `developer` | `CODE` | `ad-tdd` Phase 3 + `coding-standards` | 业务代码 + `06-code.md` |
| 3 | `verifier` | `VERIFY` | `coding-standards` GATES L0-L6 + `pr-gate` | `05-verification.md` |
| 4 | `deployer` | `DEPLOY` | `pr-gate` + Docker / Alembic | `06-deploy.md` |
| 5 | `tester` | `REGRESSION` | `golden-set` + Playwright | `07-regression.md` |

## 二、各角色协议

### 2.1 plan-generator（PLAN）

- **Read**：`TDS-<id>.md` + 上游 evidence
- **Write**：`evidence/05-plan.md` + 追加 `TDS-<id>.md` 实施计划章节（12 项自检）
- **禁用**：跑代码 / 改 Skill / 写业务代码
- **退出**：✅ 步骤有顺序 + 回滚点 + PR 拆点；⚠️ 缺回滚点 → 补；🔴 无顺序 → 退回 tech-architect

### 2.2 developer（CODE）

- **工具**：全套文件工具（受 R-5 约束）；`uv run pytest/ruff/mypy --strict`
- **Write**：`backend/app/`、`apps/`、测试代码、`evidence/06-code.md`
- **禁用**：Read `evidence/*.md` 原文（避免上下文污染）；任何 R-1~R-5 违规
- **Skill 调用**：
  - `ad-tdd/SKILL.md` Phase 3（**必串接**）—— RED → GREEN → REFACTOR 全循环
  - `coding-standards.mdc`（全程遵循）—— 节点签名、State 用 TypedDict、不硬编码 LLM 参数
  - `frontend-standards/SKILL.md`（前端任务时叠加）
- **退出**：✅ L0 ruff format + L1 pytest unit + L3 pytest integration + 覆盖率达标（rules ≥ 90%、agents/middleware ≥ 80%、整体 ≥ 60%）；🔴 L0/L1 fail → 不允许进入下一阶段

### 2.3 verifier（VERIFY）

> **A 档约束（W1 P0 修复）**：verifier 与 developer 职责**严格分离**——verifier **只检查不修**，
> L0 命令不允许 `--fix`。违规的代码**必须退回 developer 修复**，不能在 verifier 阶段被自动改。
> 避免"verifier 改完代码 → 报告 PASS → 走下一步"的假绿。
>
> **真源**：`.cursor/rules/l0-l6-gates.mdc` §一 + §六执行者矩阵 + §七阶段矩阵；硬卡数字见 `pr-gate.yml` 卡口 5（`pytest --cov-fail-under=60`）。

- **Run**：`uv run pytest tests/{integration,e2e,smoke} -x -q`；`python -m eval.runner --mode pr`（仅 Prompt 改动时）
- **Read**：`atdd/TDS-<id>-AC.md`、`evidence/04-acceptance.md`（如已存在）、`06-code.md`（developer 自审报告）
- **Write**：`evidence/05-verification.md`
- **禁用**：写 feature 代码、**自动改代码**（任何 `--fix` / `format` 写操作都禁止）、放宽阈值
- **Skill 调用**（**GATES L0-L6 全跑，但 verifier 不修复**）：

| 级别 | 命令（**只检查不修**） | 失败处理 |
|------|-----------------------|---------|
| L0 | `uv run ruff check .`（无 `--fix`） | FAIL → 退回 developer |
| L1 | `uv run ruff format --check .`（无 `--fix` 不写文件） | FAIL → 退回 developer |
| L2 | `uv run mypy --strict app/` | FAIL → 退回 developer |
| L3 | `uv run pytest tests/{integration,e2e,smoke} -x -q` | FAIL → 退回 developer |
| L4 | `uv run ruff check . --select=F401,F811,S608,S307,SEC,B,B003` | FAIL → 退回 developer |
| L6 | `uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=60`（硬卡数字，不"可能不达标"） | FAIL → 补测试或降门（走 ADR） |

- **退出**：✅ L0-L6 全 PASS + ATDD 全过 + PR-Gate 6 项 ✅；🔴 任一 L 级 FAIL → 退回 developer

### 2.4 deployer（DEPLOY）

- **Run**：`docker compose`、`alembic upgrade head / downgrade -1`、`kubectl rollout`（若 k8s）
- **Read**：`evidence/05-verification.md`、`docker-compose.yaml`、`db/init/*.sql`
- **Write**：`evidence/06-deploy.md`
- **禁用**：写 feature 代码
- **退出**：✅ 预发 5xx < 0.1% + P95 延迟达标（V3 §10.2）+ 迁移成功；🔴 迁移失败 / 健康检查红 → 触发回滚

### 2.5 tester（REGRESSION）

- **Run**：`uv run pytest tests/e2e -x -q`、`python -m eval.runner --mode pr`、Playwright
- **Read**：`backend/eval/golden_set_v*.yaml`、`baseline.json`
- **Write**：`evidence/07-regression.md`
- **禁用**：写 feature 代码
- **Skill 调用**（**`golden-set/SKILL.md` 必跑 `--mode pr`**）：baseline 跌幅 ≤ 5% 通过；> 5% 拒合入（PR-Gate 红线）
- **退出**：✅ baseline 跌幅 ≤ 5% + e2e 全 PASS + Playwright 视觉无回归；🔴 跌幅 > 5% 全局拒绝

## 三、evidence 写产物路径

| Phase | Executor | evidence 文件 |
|-------|----------|--------------|
| `PLAN` | plan-generator | `docs/harness/evidence/05-plan.md` |
| `CODE` | developer | `docs/harness/evidence/06-code.md` |
| `VERIFY` | verifier | `docs/harness/evidence/05-verification.md` |
| `DEPLOY` | deployer | `docs/harness/evidence/06-deploy.md` |
| `REGRESSION` | tester | `docs/harness/evidence/07-regression.md` |

> `05-verification.md` 与 `05-plan.md` 共用 `05-` 前缀不同主题——保留方案 §四原表。

## 四、硬禁止清单

| # | 禁止 | 兜底 |
|---|------|------|
| 1 | 在 `agents/` 内写业务规则 | R-2；grep `if.*score.*>` agents/ 必须无命中 |
| 2 | developer 漏调 `ad-tdd` Phase 3 | PR-Gate 兜底 |
| 3 | verifier 漏跑 L0-L6 任一级 | PR-Gate 兜底 |
| 4 | tester 漏跑 Golden Set `--mode pr` | PR-Gate 兜底 |
| 5 | executor 越权 Read 其他 phase evidence 原文 | 主会话上下文隔离铁律 |
| 6 | 修改 Skill / Rule / Workflow | executor 只产代码 + evidence |

## 五、退出条件总览

| Executor | 终止行为 |
|----------|---------|
| `plan-generator` | 写 `05-plan.md` + 追加 TDS 实施计划 → 通知 dispatcher 进入 CODE |
| `developer` | 写 `06-code.md` + L0-L4 PASS + 覆盖率达标 → 进入 VERIFY |
| `verifier` | 写 `05-verification.md` + L0-L6 + PR-Gate ✅ → 进入 DEPLOY |
| `deployer` | 写 `06-deploy.md` + 预发 PASS → 进入 REGRESSION |
| `tester` | 写 `07-regression.md` + baseline 跌幅 ≤ 5% → 进入 SIGN_OFF |

## 六、与其他协议文件边界

```
DISPATCHER → 状态机路由（"现在轮到哪个 executor"）
EXECUTORS（本文件）→ 5 执行角色（"我做什么 / 不做什么"）
REVIEWERS → 5 评审角色（"评审只产出观点，不写代码"）
ORCHESTRATOR → 跨角色合成（PRE_MORTEM / SIGN_OFF）
```

四份协议通过 `evidence/*.md` 路径对齐，单文件改动不强制其他三份同步。

## 七、参考

- 评审角色：`agents/harness/REVIEWERS.md`
- 合成协议：`agents/harness/ORCHESTRATOR.md`
- Skill 入口：`ad-tdd` / `coding-standards` / `pr-gate` / `golden-set` / `frontend-standards`
- 状态机：`docs/harness/workflow.yaml`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-1~R-5
