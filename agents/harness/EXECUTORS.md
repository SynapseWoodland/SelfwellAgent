---
scope: harness-protocol
contains_business_rules: false
r2_compliance: documented
owner: harness-executors
---
# EXECUTORS — 5 执行角色协议（A 档精简版）

> **A 档精简**：原 8 章 → 6 章；合并 §三 Skill 调用矩阵进 §二各角色；删 §八 参考。
> 5 个 executor 对应 `PLAN / CODE / VERIFY / DEPLOY / REGRESSION`；**只调用既有 Skill**，不重复造轮子；**所有业务代码 / 业务规则落 `backend/app/`、`apps/`、`rules/`**（R-2 红线）。

## 一、6 执行角色总览

| # | 角色 ID | phase | 主用 Skill | evidence |
|---|---------|-------|-----------|----------|
| 1 | `plan-generator` | `PLAN` | `ad-tdd` Phase 1 | `05-plan.md` + `TDS-<id>.md` 实施计划 |
| 2 | `developer` | `CODE` | `ad-tdd` Phase 3 + `coding-standards` | 业务代码 + `06-code.md` |
| 3 | `deployer` | `DEPLOY` | `pr-gate` + Docker / Alembic | `09-deploy.md` |
| 4 | `verifier` | `VERIFY` | `coding-standards` GATES L0-L6 + `pr-gate` | `07-verify.md` |
| 5 | `security-reviewer` | `SECURITY_TEST` | `python-patterns` 安全规则 | `08-security-test.md` |
| 6 | `tester` | `REGRESSION` | `golden-set` + Playwright | `10-regression.md` |

## 二、各角色协议

### 2.0 测试分层定义（业界标准）

| 类型 | 工具 | 覆盖范围 | 归属阶段 |
|------|------|---------|---------|
| **unit** | pytest `tests/unit/` | 单个函数/类逻辑 | CODE（developer 自测） |
| **integration** | pytest `tests/integration/` | 模块间交互 | VERIFY |
| **API-E2E** | pytest `tests/e2e/` | 纯后端 API 端到端 | VERIFY + REGRESSION |
| **smoke** | pytest `tests/smoke/` | 核心 API 冒烟 | VERIFY + REGRESSION |
| **UI-E2E** | 微信 MCP / Playwright | 前端 UI + 前后端联动 | VERIFY（可选）+ REGRESSION |
| **Golden Set** | Eval Runner | LLM/AI 功能回归 | REGRESSION |

### 执行阶段矩阵

| 阶段 | integration | API-E2E | smoke | UI-E2E | Golden Set |
|------|:-----------:|:--------:|:-----:|:------:|:----------:|
| **ATDD** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **VERIFY** | ✅ | ✅ | ✅ | ✅* | ❌ |
| **REGRESSION** | ❌ | ✅ | ✅ | ✅ | ✅ |

*UI-E2E 在 VERIFY 阶段为**可选**（资源充足时执行）

### ATDD 说明

ATDD 阶段**不跑自动化测试**，只产出 `.feature` 验收标准文件 + `04-atdd.md` evidence。

### REGRESSION 环境说明

REGRESSION 在**同一套 dev 环境**执行（`APP_ENV=dev`），不区分独立 staging：
- 原因：当前项目没有独立的 staging 环境
- 适用阶段：MVP 快速迭代
- UI-E2E 自动检测环境可用性，不可用时自动跳过并记录

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

> **适用任务**：feature + bugfix（仅增量测试）
> **真源**：`.cursor/rules/l0-l6-gates.mdc` §一 + §六执行者矩阵 + §七阶段矩阵；硬卡数字见 `pr-gate.yml` 卡口 5（`pytest --cov-fail-under=60`）。

- **增量识别**：基于 ATDD 用例映射（每个 FR 关联对应测试文件）
- **Run**：`uv run pytest tests/{integration,e2e,smoke} -x -q`（仅运行增量测试）；`python -m eval.runner --mode pr`（仅 Prompt 改动时）
- **Read**：`atdd/TDS-<id>-AC.md`、`evidence/04-acceptance.md`（如已存在）、`06-code.md`（developer 自审报告）
- **Write**：`evidence/07-verify.md`
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

### 2.5 security-reviewer（SECURITY_TEST）

> **并行执行**：与 VERIFY 并行，两者都完成后进入 REGRESSION。

- **Run**：`uv run ruff check . --select=S,SEC,B`（安全扫描）
- **Read**：`06-code.md`（developer 自审报告）
- **Write**：`evidence/08-security-test.md`
- **禁用**：写 feature 代码
- **Skill 调用**：`python-patterns.mdc`（安全规则）
- **退出**：✅ 安全扫描 PASS；🔴 高危漏洞 → 退回 developer

### 2.6 deployer（DEPLOY）

> **条件触发**：DEPLOY 不是每次都跑，仅当有 DDL/DML 或前端改动时执行。

**触发条件（满足任一即可）**：
- 有 DDL/DML 更新
- 有前端代码更新

**非触发（跳过 DEPLOY）**：
- 仅后端代码更新

**操作**：

| 触发类型 | 操作 |
|---------|------|
| 前端改动 | 微信开发者工具重新编译 |
| DDL/DML | `alembic upgrade head` + 额外数据脚本 |

**产出**：`evidence/09-deploy.md`（包含"跳过"或"执行"记录）

**退出**：✅ evidence 写入成功；🔴 部署失败 → 退回 developer

### 2.6 developer（DOC_FIX）

> **适用任务**：文档修复（无运行时验证）

- **Run**：
  - `uv run ruff format --check .`（Markdown 格式检查）
  - `typos --format brief`（拼写检查）
  - `markdownlint **/*.md`（Markdown 语法检查）
  - broken-link-checker（链接检查）
- **Read**：`evidence/06-code.md`（如涉及代码文档）
- **Write**：`evidence/17-doc-fix.md`
- **禁用**：写 feature 代码、运行 pytest
- **Skill 调用**：`coding-standards.mdc`（文档规范）
- **退出**：✅ 文档检查全 PASS；🔴 格式/链接错误 → 修复后重跑

### 2.7 tester（REGRESSION）

> **环境说明**：REGRESSION 在 dev 环境执行（与 VERIFY 同一套 docker-compose），不区分独立 staging。

- **Run**：
  - `uv run pytest tests/e2e -x -q`
  - `python -m eval.runner --mode pr`（Golden Set）
  - Playwright / 微信 MCP（UI-E2E，自动检测可用性）
- **Read**：`backend/eval/golden_set_v*.yaml`、`baseline.json`
- **Write**：`evidence/10-regression.md`
- **禁用**：写 feature 代码
- **Skill 调用**（**`golden-set/SKILL.md` 必跑 `--mode pr`**）：baseline 跌幅 ≤ 5% 通过；> 5% 拒合入（PR-Gate 红线）
- **UI-E2E 自动跳过机制**：
  - 微信 MCP：检测 Windows + 微信开发者工具是否可用
  - Playwright：检测浏览器是否可用
  - 不可用时跳过并记录原因到 evidence
- **退出**：✅ baseline 跌幅 ≤ 5% + e2e 全 PASS + UI-E2E 无回归（如可用）；🔴 跌幅 > 5% 全局拒绝

## 三、evidence 写产物路径

| Phase | Executor | evidence 文件 |
|-------|----------|--------------|
| `PLAN` | plan-generator | `harness/evidence/05-plan.md` |
| `CODE` | developer | `harness/evidence/06-code.md` |
| `DEPLOY` | deployer | `harness/evidence/09-deploy.md` |
| `VERIFY` | verifier | `harness/evidence/07-verify.md` |
| `SECURITY_TEST` | security-reviewer | `harness/evidence/08-security-test.md` |
| `DOC_FIX` | developer | `harness/evidence/17-doc-fix.md` |
| `REGRESSION` | tester | `harness/evidence/10-regression.md` |

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
| `developer`（CODE） | 写 `06-code.md` + L0-L4 PASS + 覆盖率达标 → 进入 DEPLOY |
| `deployer` | 写 `09-deploy.md` + 部署成功/跳过 → 进入 VERIFY |
| `verifier` | 写 `07-verify.md` + L0-L6 + PR-Gate ✅ → 进入 REGRESSION |
| `security-reviewer` | 写 `08-security-test.md` + 安全扫描 PASS → 进入 REGRESSION |
| `developer`（DOC_FIX） | 写 `17-doc-fix.md` + 文档检查 PASS → 进入 SIGN_OFF |
| `tester` | 写 `10-regression.md` + baseline 跌幅 ≤ 5% → 进入 SIGN_OFF |

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
- 状态机：`harness/workflow.yaml`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-1~R-5
