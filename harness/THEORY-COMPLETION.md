# Harness 理论收尾 — THEORY-COMPLETION.md

> **目的**：填平 workflow-v2.yaml 的理论空白，使 Demo 跑通有据可依。
>
> **覆盖范围**：16 phase exit_criteria 审计、harness_cli.py 最低可用版设计、Demo 成功标准、阻塞项清单。
>
> **状态**：本文档为理论补全，不实现代码；所有代码任务落入 `harness/checklist-now.md` 或 `harness/checklist-future.md`。

---

## 目录

1. [16 Phase Exit_Criteria 审计](#一-16-phase-exit_criteria-审计)
2. [harness_cli.py 最低可用版设计](#二-harness_cli-py-最低可用版设计)
3. [Demo 成功标准](#三-demo-成功标准)
4. [阻塞项清单](#四-阻塞项清单)

---

## 一、16 Phase Exit_Criteria 审计

### 1.1 审计方法

- **真源**：`harness/workflow-v2.yaml` 的 `exit_criteria` 字段
- **判定规则**：
  - ✅ **已有**：3 条命令全部具体，无占位符
  - ⚠️ **部分缺失**：有占位符（如 `<feature>`）或正则过于宽松
  - ❌ **缺失**：无 exit_criteria 定义
- **Demo 必要性**：P0 = 必须有才能跑 Demo；P1 = Demo 后补充；P2 = 可选

### 1.2 审计结果总览

| # | Phase ID | 入口 Agent | Criteria 数 | 状态 | Demo 必要性 |
|---|----------|------------|-------------|------|-------------|
| 1 | PRD | requirement-analyst | 3 | ✅ 已有 | P0 |
| 2 | ARCH_DESIGN | tech-architect | 3 | ✅ 已有 | P0 |
| 3 | PRE_MORTEM | requirement-analyst | 3 | ✅ 已有 | P0 |
| 4 | ATDD | quality-guardian | 3 | ⚠️ 部分缺失 | P0 |
| 5 | PLAN | plan-generator | 3 | ✅ 已有 | P0 |
| 6 | CODE | developer | 3 | ⚠️ 部分缺失 | P0 |
| 7 | VERIFY | verifier | 3 | ⚠️ 部分缺失 | P0 |
| 8 | SECURITY_TEST | security-reviewer | 3 | ⚠️ 部分缺失 | P1 |
| 9 | DEPLOY | deployer | 3 | ⚠️ 部分缺失 | P1 |
| 10 | REGRESSION | tester | 3 | ✅ 已有 | P0 |
| 11 | SIGN_OFF | requirement-analyst | 3 | ✅ 已有 | P0 |
| 12 | DATA_REPLAY | requirement-analyst | 3 | ✅ 已有 | P2 |
| 13 | INCIDENT_RESPONSE | deployer | 3 | ✅ 已有 | P2 |
| 14 | OPS_LOOP | tester | 3 | ✅ 已有 | P2 |
| 15 | SKILL_UPDATE | quality-guardian | 3 | ⚠️ 部分缺失 | P2 |
| 16 | INTERRUPT_REVIEW | quality-guardian | 3 | ✅ 已有 | P2 |

**汇总**：✅ 已有 10 个 | ⚠️ 部分缺失 5 个 | ❌ 缺失 0 个

---

### 1.3 逐 phase 分析与补全建议

#### Phase 1 — PRD ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/01-requirement.md'
  - 'grep -q "^signed: true" harness/evidence/01-requirement.md'
  - 'grep -qE "fr_refs:.*FR-[A-Z0-9]+-[0-9]+-[0-9]{8}" harness/evidence/01-requirement.md'
```

**分析**：3 条完整，frontmatter 格式固定，无问题。

**补充建议（可选）**：增加内容行数下限，避免空文件满足条件。

```yaml
  - 'wc -l < harness/evidence/01-requirement.md | awk "{print $1}" | grep -qE "[2-9][0-9]+|[0-9]{3,}"'
```

---

#### Phase 2 — ARCH_DESIGN ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/02-tech-design.md'
  - 'grep -q "^signed: true" harness/evidence/02-tech-design.md'
  - 'grep -qE "adr_refs:.*ADR-[0-9]" harness/evidence/02-tech-design.md'
```

**分析**：3 条完整，ADR 编号格式合理。

---

#### Phase 3 — PRE_MORTEM ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/03-pre-mortem.md'
  - 'grep -q "^signed: true" harness/evidence/03-pre-mortem.md'
  - 'grep -qE "fr_refs:.*FR-[A-Z0-9]+-[0-9]+-[0-9]{8}" harness/evidence/03-pre-mortem.md'
```

**分析**：3 条完整，支持 `one_person_synthesis: true` 模式（由 orchestrator 合成，无需 5 reviewer）。

---

#### Phase 4 — ATDD ⚠️ 部分缺失

```yaml
exit_criteria:
  - 'test -f harness/evidence/04-atdd.md'
  - 'grep -q "^signed: true" harness/evidence/04-atdd.md'
  - 'test -f backend/tests/atdd/<feature>.feature && grep -q "Scenario" backend/tests/atdd/<feature>.feature'
```

**问题**：第 3 条含 `<feature>` 占位符，Demo 时必须替换为具体 feature 名（如 `wx-login.feature`）。

**P0 补全（Demo 前必须修复）**：

```yaml
  # 方案 A：固定 feature 文件名（Demo 推荐）
  - 'test -f backend/tests/atdd/wx-login.feature && grep -q "Scenario" backend/tests/atdd/wx-login.feature'
  # 方案 B：通配符匹配（通用性更好）
  - 'ls backend/tests/atdd/*.feature | wc -l | grep -qE "[1-9]"'
```

> **决策**：Demo 阶段用方案 A（固定 `wx-login.feature`）；后续用方案 B。

---

#### Phase 5 — PLAN ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/05-plan.md'
  - 'grep -q "^signed: true" harness/evidence/05-plan.md'
  - 'grep -qE "fr_refs:.*FR-[A-Z0-9]+-[0-9]+-[0-9]{8}" harness/evidence/05-plan.md'
```

**分析**：3 条完整。

---

#### Phase 6 — CODE ⚠️ 部分缺失

```yaml
exit_criteria:
  - 'test -f harness/evidence/06-code.md'
  - 'grep -q "^signed: true" harness/evidence/06-code.md'
  - 'cd backend && uv run pytest tests/unit -x -q --tb=no >/dev/null 2>&1'
```

**问题**：
1. 第 3 条 pytest 命令重定向到 `/dev/null`，check_phase.py 在 Windows 下执行会失败
2. 仅检查 `tests/unit`，缺少对 `rules/`、`agents/` 等高门槛模块的覆盖率检查

**P0 补全建议**：

```yaml
  # 修复 Windows 兼容性 + 更严格的检查
  - 'cd backend && uv run pytest tests/unit -x -q --tb=no'
  # 可选：coverage 门槛（L6 下沉到 CODE 阶段提前卡）
  # Demo 阶段可省略，VERIFY 阶段已覆盖
```

> **注**：`/dev/null` 在 Windows PowerShell 中不存在，check_phase.py 已通过 Python subprocess 规避此问题，但 pytest 命令本身应避免重定向。

---

#### Phase 7 — VERIFY ⚠️ 部分缺失

```yaml
exit_criteria:
  - 'test -f harness/evidence/07-verify.md'
  - 'grep -q "^signed: true" harness/evidence/07-verify.md'
  - 'grep -qE "(L0|L1|L3).*PASS|ruff.*pass|pytest.*pass" harness/evidence/07-verify.md'
```

**问题**：第 3 条正则过于宽松，只要 evidence 文档中出现 PASS 关键字即通过，无法防止漏跑 L0-L6。

**P0 补全建议**（将 EXECUTORS.md §2.3 的 L0-L6 命令落地为可执行检查）：

```yaml
  # 方案 A：直接执行 L0-L6 命令（最严格）
  - 'cd backend && uv run ruff check . --select=E722 >/dev/null 2>&1'  # L0
  - 'cd backend && uv run ruff format --check . >/dev/null 2>&1'        # L1
  - 'cd backend && uv run mypy --strict app/ >/dev/null 2>&1'          # L2
  - 'cd backend && uv run pytest tests/integration -x -q --tb=no >/dev/null 2>&1'  # L3
  # 方案 B：依赖 evidence 文档内容（宽松但实用）
  - 'grep -q "L0.*PASS" harness/evidence/07-verify.md && grep -q "L2.*PASS" harness/evidence/07-verify.md'
```

> **决策**：Demo 阶段用方案 B（依赖 verifier 报告）；生产环境用方案 A。

---

#### Phase 8 — SECURITY_TEST ⚠️ 部分缺失

```yaml
exit_criteria:
  - 'test -f harness/evidence/08-security-test.md'
  - 'grep -q "^signed: true" harness/evidence/08-security-test.md'
  - 'cd backend && uv run ruff check . --select=S,SEC,B >/dev/null 2>&1'
```

**问题**：Demo 阶段可能跳过 SECURITY_TEST（P1），但定义已存在，仅需确认此 phase 在 Pilot FR 中是否激活。

**P1 补全**：保持现状，Demo 后激活。

---

#### Phase 9 — DEPLOY ⚠️ 部分缺失

```yaml
exit_criteria:
  - 'test -f harness/evidence/09-deploy.md'
  - 'grep -q "^signed: true" harness/evidence/09-deploy.md'
  - 'grep -qE "deploy.*success|部署成功" harness/evidence/09-deploy.md'
```

**问题**：第 3 条仅检查 evidence 文档中是否有"成功"字样，无法验证真实的部署状态。

**P1 补全建议**：

```yaml
  # 方案 A：检查 docker compose 健康状态（需要 Docker 运行时）
  - 'docker compose ps --format json | grep -q "healthy"'  # 假设容器名为 app
  # 方案 B：检查健康端点
  - 'curl -sf http://localhost:8000/health || exit 1'
  # 方案 C：仅依赖 evidence 文档（Demo 阶段可行）
  - 'grep -qE "(deploy.*success|部署成功|health.*ok)" harness/evidence/09-deploy.md'
```

> **决策**：Demo 阶段用方案 C（文档验证）；有 Docker 环境后升级为方案 A/B。

---

#### Phase 10 — REGRESSION ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/10-regression.md'
  - 'grep -q "^signed: true" harness/evidence/10-regression.md'
  - 'cd backend && uv run pytest tests/integration -x -q --tb=no >/dev/null 2>&1'
```

**分析**：3 条完整，pytest integration 检查合理。

> **注**：同 CODE phase，Windows 下 `/dev/null` 问题已由 check_phase.py 规避。

---

#### Phase 11 — SIGN_OFF ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/11-signoff.md'
  - 'grep -q "^signed: true" harness/evidence/11-signoff.md'
  - 'grep -qE "fr_refs:.*FR-[A-Z0-9]+-[0-9]+-[0-9]{8}" harness/evidence/11-signoff.md'
```

**分析**：3 条完整，支持 `one_person_synthesis: true` 模式。

---

#### Phase 12 — DATA_REPLAY ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/12-data-replay.md'
  - 'grep -qE "replay_session_id: [a-f0-9-]{36}" harness/evidence/12-data-replay.md'
  - 'grep -qE "fr_refs:.*FR-[A-Z0-9]+-[0-9]+-[0-9]{8}" harness/evidence/12-data-replay.md'
```

**分析**：3 条完整，UUID 格式校验合理。

---

#### Phase 13 — INCIDENT_RESPONSE ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/13-incident-response.md'
  - 'grep -q "^signed: true" harness/evidence/13-incident-response.md'
  - 'grep -qE "(fr_refs|incident_id).*FR-|INC-" harness/evidence/13-incident-response.md'
```

**分析**：3 条完整，INC 前缀支持事故单编号。

---

#### Phase 14 — OPS_LOOP ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/14-ops-loop.md'
  - 'grep -q "^signed: true" harness/evidence/14-ops-loop.md'
  - 'grep -qE "(A/B|灰度|gradual)" harness/evidence/14-ops-loop.md'
```

**分析**：3 条完整，灰度策略关键词覆盖合理。

---

#### Phase 15 — SKILL_UPDATE ⚠️ 部分缺失

```yaml
exit_criteria:
  - 'test -f harness/evidence/15-skill-update.md'
  - 'grep -q "^signed: true" harness/evidence/15-skill-update.md'
  - 'ls harness/lessons/ | wc -l | grep -qE "[1-9]"'
```

**问题**：第 3 条仅检查 `harness/lessons/` 目录有文件，但未验证 lesson 文件的 frontmatter 格式。

**P2 补全建议**：

```yaml
  # 验证 lesson 文件不是空目录 + frontmatter 有效
  - 'find harness/lessons/ -name "*.md" -exec grep -q "^---" {} \; && find harness/lessons/ -name "*.md" | wc -l | grep -qE "[1-9]"'
```

---

#### Phase 16 — INTERRUPT_REVIEW ✅

```yaml
exit_criteria:
  - 'test -f harness/evidence/16-interrupt-review.md'
  - 'grep -q "^signed: true" harness/evidence/16-interrupt-review.md'
  - 'grep -qE "(resume|continue|推迟|defer)" harness/evidence/16-interrupt-review.md'
```

**分析**：3 条完整，包含决策关键词覆盖。

---

### 1.4 Exit_Criteria 补全汇总表

| Phase | 状态 | 优先级 | 建议操作 | Demo 前必须？ |
|-------|------|--------|----------|-------------|
| PRD | ✅ | — | 可选：增加内容行数下限 | — |
| ARCH_DESIGN | ✅ | — | 无 | — |
| PRE_MORTEM | ✅ | — | 无 | — |
| ATDD | ⚠️ | **P0** | 将 `<feature>` 替换为 `wx-login` | ✅ 必须 |
| CODE | ⚠️ | **P0** | 移除 `/dev/null` 重定向 | ✅ 必须 |
| VERIFY | ⚠️ | **P0** | 收紧正则或改为直接执行 L0-L6 | ✅ 必须 |
| SECURITY_TEST | ⚠️ | P1 | 确认 Demo 是否激活 | — |
| DEPLOY | ⚠️ | P1 | 增加健康检查或保持文档验证 | — |
| REGRESSION | ✅ | — | 无 | — |
| SIGN_OFF | ✅ | — | 无 | — |
| DATA_REPLAY | ✅ | P2 | 无 | — |
| INCIDENT_RESPONSE | ✅ | P2 | 无 | — |
| OPS_LOOP | ✅ | P2 | 无 | — |
| SKILL_UPDATE | ⚠️ | P2 | 增加 frontmatter 格式校验 | — |
| INTERRUPT_REVIEW | ✅ | P2 | 无 | — |

**P0 行动项**（3 项，Demo 前必须完成）：

1. ATDD exit_criteria 第 3 条：将 `<feature>` → `wx-login`
2. CODE exit_criteria 第 3 条：移除 `>/dev/null 2>&1` 后缀
3. VERIFY exit_criteria 第 3 条：收紧正则或改用直接执行 L0-L6

---

## 二、harness_cli.py 最低可用版设计

> **说明**：本文档为设计文档，不实现代码。完整实现落入 `harness/checklist-future.md` §7.6。

### 2.1 核心功能清单（Minimum Viable）

| # | 功能 | 说明 | 优先级 | Demo 相关性 |
|---|------|------|--------|-------------|
| F1 | **状态持久化** | 读写 `harness/state/harness-state.json` | P0 | Demo 必需 |
| F2 | **Phase 续跑** | 从中断的 phase 恢复，而非从头开始 | P0 | Demo 必需 |
| F3 | **Phase 跳转** | 手动指定下一个 phase（如 PRD → CODE）| P1 | 调试有用 |
| F4 | **Batch 模式** | 批量执行多个 FR（`--batch FR1,FR2`）| P2 | Demo 后 |
| F5 | **Auto 模式** | 连续执行直到完成（`--auto`）| P1 | Demo 必需 |
| F6 | **Dry Run** | 仅显示下一个 phase，不执行（`--dry-run`）| P1 | 调试有用 |
| F7 | **Snapshot** | 中断前自动保存状态快照 | P2 | Demo 后 |

### 2.2 CLI 接口设计

```bash
# 最低可用版（Demo 必须）
python harness_cli.py run                      # 从 current_phase 继续执行
python harness_cli.py run --phase PRD          # 从指定 phase 开始
python harness_cli.py status                   # 显示当前状态（state.json 摘要）
python harness_cli.py init --fr FR-PILOT-001  # 初始化新 FR

# 扩展功能（Demo 后）
python harness_cli.py run --batch FR-001,FR-002,FR-003  # 批量执行
python harness_cli.py run --auto              # 自动连续执行
python harness_cli.py run --dry-run           # 仅预览，不执行
python harness_cli.py snapshot                # 手动保存快照
python harness_cli.py reset --phase PRD       # 重置指定 phase
```

### 2.3 数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                         harness_cli.py                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐│
│  │  CLI Parser  │──▶│ StateManager │──▶│ PhaseRunner          ││
│  │  (argparse)  │   │  (F1 持久化) │   │ (调用 agent / 写 evidence) ││
│  └──────────────┘   └──────┬───────┘   └──────────┬───────────┘│
│                            │                      │            │
│                            ▼                      ▼            │
│                   ┌────────────────┐      ┌─────────────────┐ │
│                   │state.json      │      │ check_phase.py  │ │
│                   │(F1 状态存储)   │      │ (验证 exit_criteria)│
│                   └────────────────┘      └────────┬────────┘ │
│                                                     │          │
└─────────────────────────────────────────────────────┼──────────┘
                                                      │
                                    ┌─────────────────┴─────────┐
                                    │  workflow-v2.yaml         │
                                    │  (16 phase 定义)           │
                                    └───────────────────────────┘
```

### 2.4 状态转换逻辑

```
init
  └─▶ PRD ──▶ ARCH_DESIGN ──▶ PRE_MORTEM ──▶ ATDD
              │                                        │
              ▼                                        │
           [中断] ◀────────────────────────────────────┘
              │                                             
              ▼                                             
        INTERRUPT_REVIEW (budget > 0)
              │                                             
              ├── budget > 0: resume_from = $interrupted_phase
              └── budget = 0: AskUser

续跑 (resume)
  └─▶ 读取 state.json
        └─▶ current_phase
              └─▶ 读取 workflow-v2.yaml next[]
                    └─▶ 执行下一 phase
                          └─▶ 调用 check_phase.py
                                └─▶ 全部 PASS：写入 state.json，更新 current_phase
                                └─▶ 任一 FAIL：中断，写入 interrupt_stack
```

### 2.5 核心模块设计

```
harness_cli.py/
├── cli.py              # argparse CLI 入口
├── state_manager.py    # F1 状态读写
│   ├── load() → HarnessState
│   ├── save(state) → None
│   └── update_phase(phase_id) → None
├── phase_runner.py     # F2/F5 phase 执行
│   ├── run_phase(phase_id) → ExitResult
│   ├── check_criteria(phase_id) → bool
│   └── auto_loop() → None
└── exceptions.py       # 异常定义
    ├── PhaseExitNotMet   # exit_criteria 未满足
    ├── InterruptBudgetExhausted  # budget 耗尽
    └── InvalidStateError  # state.json 格式错误
```

### 2.6 与 check_phase.py 的关系

| 工具 | 职责 | 依赖关系 |
|------|------|---------|
| `check_phase.py` | 纯检查：读取 workflow-v2.yaml，执行 exit_criteria | 被 harness_cli.py 调用 |
| `harness_cli.py` | 编排：管理状态、控制流程、调用 check_phase.py | 调用 check_phase.py |

```
harness_cli.py (编排层)
  ├── 调用 check_phase.py (检查层)
  │     └── 读取 workflow-v2.yaml
  └── 读写 state.json (持久层)
```

> **注**：harness_cli.py 不重复 check_phase.py 的逻辑，而是将 check_phase.py 作为子进程调用，保持职责分离。

---

## 三、Demo 成功标准

### 3.1 可量化指标（必须全部满足）

| # | 指标 | 阈值 | 测量方法 | P0/P1 |
|---|------|------|---------|--------|
| M1 | **16 phase 全部走完** | 16/16 | state.json phase_history 包含全部 16 个 phase | **P0** |
| M2 | **Exit_Criteria 通过率** | 16/16 phase 的全部 criteria 通过 | `python check_phase.py --all` 全部 PASS | **P0** |
| M3 | **代码质量** | L0~L3 全部 PASS | VERIFY phase pytest / ruff / mypy | **P0** |
| M4 | **Pilot FR 实现** | 至少 1 个 FR 从 PRD 到 SIGN_OFF | evidence 文件完整性 | **P0** |
| M5 | **中断-续跑成功** | 至少 1 次人为中断（设 signed: false）后成功续跑 | interrupt_stack 有记录 + 续跑后 phase 完成 | **P0** |
| M6 | **Lesson 沉淀** | 至少 1 份 lesson 文件 | `harness/lessons/` 有文件 | P1 |
| M7 | **覆盖率** | 整体 ≥ 60%（L6 门槛） | pytest --cov | P1 |

### 3.2 不可量化但必须满足的条件

| # | 条件 | 验证方法 | P0/P1 |
|---|------|---------|--------|
| C1 | **Pilot FR 有实际业务价值** | 不是 hello-world，必须是真实 FR（如微信登录 `ATDD-M1`） | **P0** |
| C2 | **Evidence 内容有实质深度** | 每个 evidence 文件 ≥ 50 行，包含真实的分析/设计/评审内容 | **P0** |
| C3 | **无虚假满足** | 不能通过写空文件/假内容绕过 exit_criteria | **P0** |
| C4 | **中断机制真实可用** | interrupt_budget 计数正确，耗尽后正确触发 AskUser | **P0** |
| C5 | **所有 Agent 角色均已调用** | phase_history 中至少有 4 种不同 agent 出现（requirement-analyst / tech-architect / quality-guardian / developer） | P1 |
| C6 | **ADR 决策已记录** | ARCH_DESIGN evidence 中有 ≥ 1 条 ADR 决策 | P1 |
| C7 | **Git commit 存在** | evidence 文件已提交到 git（可追溯） | P1 |

### 3.3 Demo 成功判定矩阵

```
                          P0 (必须)              P1 (期望)
                         ┌────────────┐        ┌────────────┐
量化指标 全部满足        │    ✅      │        │    ✅      │
(M1~M5 全部通过)         │  Demo成功   │        │            │
                         └────────────┘        └────────────┘
                         ┌────────────┐        ┌────────────┐
量化指标 部分满足        │    ❌      │        │    ⚠️      │
(M1~M5 有 FAIL)         │  禁止合入   │        │  条件通过   │
                         └────────────┘        └────────────┘
```

### 3.4 Demo 成功证据清单

跑完 Pilot FR 后，必须能展示以下证据：

```
harness/
├── evidence/
│   ├── 01-requirement.md        ✅ signed: true + fr_refs 有效
│   ├── 02-tech-design.md       ✅ signed: true + adr_refs ≥ 1
│   ├── 03-pre-mortem.md        ✅ signed: true
│   ├── 04-atdd.md              ✅ signed: true + *.feature 文件存在
│   ├── 05-plan.md              ✅ signed: true + fr_refs 有效
│   ├── 06-code.md              ✅ signed: true
│   ├── 07-verify.md            ✅ signed: true + L0~L3 PASS 记录
│   ├── 08-security-test.md     ⚠️ Demo 可跳过（P1）
│   ├── 09-deploy.md            ⚠️ Demo 可跳过（P1）
│   ├── 10-regression.md        ✅ signed: true
│   └── 11-signoff.md           ✅ signed: true + fr_refs 有效
├── state/
│   └── harness-state.json      ✅ phase_history 含 16 条记录
├── lessons/
│   └── *.md                    ⚠️ 至少 1 份（P1）
└── scripts/
    └── check_phase.py          ✅ --all 全部 PASS
```

---

## 四、阻塞项清单

### 4.1 阻塞分类

| 分类 | 定义 |
|------|------|
| **P0 阻塞** | 没有这个就跑不了 Demo，必须今天完成 |
| **P1 阻塞** | 没有这个 Demo 能跑但不完整，建议 Demo 前完成 |
| **P2 阻塞** | Demo 后补充，暂不影响 Demo |

### 4.2 P0 阻塞项（今天必须完成）

| # | 阻塞项 | 当前状态 | 修复方法 | 负责 |
|---|--------|---------|---------|------|
| B1 | **ATDD exit_criteria 含 `<feature>` 占位符** | ⚠️ 部分缺失 | 将 `<feature>` 替换为 `wx-login` | 修改 workflow-v2.yaml |
| B2 | **Pilot FR 未选定** | ❌ 无 | 选择 ATDD-M1（微信登录）作为 Pilot FR | 用户决策 |
| B3 | **state.json 未初始化 Pilot FR 状态** | ⚠️ 已有占位符 | 创建 `FR-PILOT-ATDD-M1-20260720` 运行 | 运行 harness_cli.py init |
| B4 | **PRD evidence 不存在** | ❌ 无 | 启动 PRD phase，生成 01-requirement.md | requirement-analyst agent |
| B5 | **VERIFY exit_criteria 过于宽松** | ⚠️ 部分缺失 | 收紧正则或改用直接执行 L0-L6 | 修改 workflow-v2.yaml |
| B6 | **CODE exit_criteria 含 `/dev/null` 重定向** | ⚠️ 部分缺失 | 移除 `>/dev/null 2>&1` | 修改 workflow-v2.yaml |

**B1/B5/B6 修复脚本**（一次性完成）：

```bash
# 修复 workflow-v2.yaml 中的 3 处 P0 问题
# 1. ATDD: <feature> -> wx-login
sed -i 's|backend/tests/atdd/<feature>.feature|backend/tests/atdd/wx-login.feature|g' harness/workflow-v2.yaml
# 2. CODE: 移除 /dev/null
sed -i 's| >/dev/null 2>&1'"'"'  # pytest unit|| >'"'"'  # pytest unit|g' harness/workflow-v2.yaml
# 3. VERIFY: 收紧正则
sed -i 's|grep -qE "(L0|L1|L3).*PASS|ruff.*pass|pytest.*pass"|grep -q "L0.*PASS.*L2.*PASS.*L3.*PASS"|g' harness/workflow-v2.yaml
```

> **注**：sed 命令仅作说明，实际修改应通过 StrReplace 工具完成。

### 4.3 P1 阻塞项（Demo 前建议完成）

| # | 阻塞项 | 说明 | 修复方法 |
|---|--------|------|---------|
| B7 | **harness_cli.py 不存在** | 无法自动化续跑，只能手动管理 state.json | 实现 F1+F2（状态持久化 + phase 续跑）|
| B8 | **DEPLOY exit_criteria 过于宽松** | 仅检查文档关键字，无法验证真实部署 | 增加 Docker 健康检查或保持现状（Demo 用文档验证）|
| B9 | **SECURITY_TEST phase 未激活** | Demo 可以跳过，但应有明确注释 | 在 workflow-v2.yaml 中标注 Demo 跳过路径 |
| B10 | **Pilot FR ATDD feature 文件不存在** | 需要 `backend/tests/atdd/wx-login.feature` | 由 ATDD phase agent 创建 |

### 4.4 P2 阻塞项（Demo 后补充）

| # | 阻塞项 | 说明 | 后续任务 |
|---|--------|------|---------|
| B11 | **Batch 模式不可用** | 只能跑单个 FR | 实现 harness_cli.py F4 |
| B12 | **SKILL_UPDATE exit_criteria 缺少 frontmatter 校验** | 仅检查目录非空 | 补全正则 |
| B13 | **Snapshot 机制不可用** | 中断前无自动快照 | 实现 harness_cli.py F7 |
| B14 | **Lesson 库为空** | 无经验沉淀 | Demo 后跑 harness-autolearn |
| B15 | **DATA_REPLAY 未验证** | 仅定义了，未实测 | Demo 后跑回放演练 |
| B16 | **INCIDENT_RESPONSE 未验证** | 仅定义了，未实测 | Demo 后跑故障演练 |
| B17 | **OPS_LOOP 未验证** | 灰度策略未实测 | Demo 后跑 A/B 演练 |

### 4.5 阻塞项优先级汇总

```
P0 (今天必须)    : B1 B2 B3 B4 B5 B6  →  6 项，阻塞 Demo
P1 (Demo 前建议) : B7 B8 B9 B10        →  4 项，影响 Demo 完整性
P2 (Demo 后)     : B11 B12 B13 B14 B15 B16 B17  →  7 项，不影响 Demo
─────────────────────────────────────────────────────
合计             : 17 项阻塞项
```

---

## 五、附录：Exit_Criteria 正则修复建议

### 5.1 修复清单（直接替换 workflow-v2.yaml）

> **原则**：保持 3 条结构（文件存在性 + signed + 内容完整性），仅修复具体命令。

| Phase | 当前命令（有问题） | 修复后命令 |
|-------|-------------------|-----------|
| ATDD #3 | `test -f backend/tests/atdd/<feature>.feature && grep -q "Scenario" backend/tests/atdd/<feature>.feature` | `test -f backend/tests/atdd/wx-login.feature && grep -q "Scenario" backend/tests/atdd/wx-login.feature` |
| CODE #3 | `cd backend && uv run pytest tests/unit -x -q --tb=no >/dev/null 2>&1` | `cd backend && uv run pytest tests/unit -x -q --tb=no` |
| VERIFY #3 | `grep -qE "(L0\|L1\|L3).*PASS\|ruff.*pass\|pytest.*pass" harness/evidence/07-verify.md` | `grep -q "L0.*PASS" harness/evidence/07-verify.md && grep -q "L2.*PASS" harness/evidence/07-verify.md && grep -q "L3.*PASS" harness/evidence/07-verify.md` |

---

## 六、附录：harness_cli.py 最小代码骨架

> 完整实现见 `harness/checklist-future.md` §7.6。

```python
# harness/scripts/harness_cli.py (设计草稿，不实现)
"""Harness CLI — Minimum Viable.

仅实现 F1（状态持久化）+ F2（phase 续跑）。
完整版见 checklist-future.md §7.6。
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json

WORKFLOW_YAML = Path(__file__).parents[2] / "harness" / "workflow-v2.yaml"
STATE_JSON = Path(__file__).parents[2] / "harness" / "state" / "harness-state.json"
EVIDENCE_DIR = Path(__file__).parents[2] / "harness" / "evidence"


@dataclass(frozen=True, slots=True)
class HarnessState:
    run_id: str
    current_phase: str
    phase_history: list[dict] = field(default_factory=list)
    interrupt_budget: int = 5
    interrupt_stack: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "HarnessState":
        with path.open() as f:
            data = json.load(f)
        return cls(run_id=data["run_id"], current_phase=data["current_phase"],
                   phase_history=data.get("phase_history", []),
                   interrupt_budget=data.get("interrupt_budget", 5),
                   interrupt_stack=data.get("interrupt_stack", []))

    def save(self, path: Path) -> None:
        data = {
            "run_id": self.run_id,
            "current_phase": self.current_phase,
            "phase_history": self.phase_history,
            "interrupt_budget": self.interrupt_budget,
            "interrupt_stack": self.interrupt_stack,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def next_phase(workflow: dict, current: str) -> str | None:
    for p in workflow.get("phases", []):
        if p["id"] == current:
            candidates = p.get("next", [])
            return candidates[0] if candidates else None
    return None


def run_phase(state: HarnessState, phase_id: str) -> bool:
    """调用 check_phase.py 验证 exit_criteria."""
    import subprocess
    result = subprocess.run(
        ["python", "harness/scripts/check_phase.py", phase_id],
        capture_output=True, text=True
    )
    return result.returncode == 0
```

---

## 七、附录：状态转移图（文本版）

```
PRD ──▶ ARCH_DESIGN ──▶ PRE_MORTEM ──▶ ATDD ──▶ PLAN
                                                           │
                                                           ▼
                              ┌─────────────────────────────┘
                              ▼
                            CODE ──▶ VERIFY ──▶ SECURITY_TEST
                                                           │
                                                           ▼
    ┌───────────────────────────────────────────────────────┘
    ▼
DEPLOY ──▶ REGRESSION ──▶ SIGN_OFF ──▶ INCIDENT_RESPONSE
                                                          │
                                                          ▼
                                                    OPS_LOOP
                                                          │
                                                          ▼
                                                   SKILL_UPDATE
                                                          │
                                                          ▼
                                                ◀── INTERRUPT_REVIEW
                                                      (budget > 0 时返回)
                                                      (budget = 0 时 AskUser)

中断路径：
任意 phase ──[interrupt]──▶ INTERRUPT_REVIEW ──[budget > 0]──▶ resume_from
                              │
                              └──[budget = 0]──▶ AskUser

回放路径：
DATA_REPLAY ──▶ PRD ──▶ (同上)
```

---

> **本文档状态**：理论补全，不含代码实现。
> **下次更新**：P0 阻塞项修复后（预计完成时间：今天）。
> **配套文件**：`harness/checklist-now.md`（Demo 实施 Checklist）、`harness/checklist-future.md`（远期规划）。
