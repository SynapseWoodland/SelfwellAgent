---
name: ad-tdd
description: >
  告知 cursor agent 实施计划，cursor agent 开始编写代码时触发。
  工作流：Architecture（架构设计）→ ATDD（验收标准）→ TDD（测试驱动开发）→ Refactor → 全量回归 → AI 自审 → Git Commit。
  代码实施阶段必须严格遵循 coding-standards SKILL.md（L0-L6 质量门禁）。
disable-model-invocation: false
---

# AD → ATDD → TDD 开发流

> **命名说明**：`ad-tdd` = Architecture Design + Acceptance Test-Driven Development + Test-Driven Development
>

## 一、Harness 链路对照

| 阶段 | 节点 | Selfwell 对应 |
|------|------|--------------|
| **Architecture** | 方案设计 → 方案确认 → Pre-Mortem → 实施计划 | `docs/spec/TDS-M*.md` |
| **ATDD** | 验收标准确认（Given-When-Then） | `docs/harness/atdd/TDS-M*-AC.md` |
| **TDD** | 开发 → 编译 → 单测 | `backend/tests/unit/` |
| **Verification** | ATDD 跑分 → 证据链 | `backend/tests/integration/` |
| **Deploy** | 部署预发 → 接口测试 | CI/CD |
| **Sign-off** | 上线确认 → 验收报告 | PR Review |

---

## 二、文档体系说明

| 文档类型 | 路径 | 用途 | 对应 Harness |
|---------|------|------|-------------|
| **PRD** | `docs/PRD/` | 产品需求层：产品要做什么 | 需求评审 |
| **Scenarios** | `docs/scenarios/` | 用户视角拆解：用户怎么用 | 需求确认 |
| **TDS** | `docs/spec/TDS-M*.md` | 技术设计文档：代码怎么实现 | 方案设计 + 实施计划 |
| **ATDD** | `docs/harness/atdd/` | 验收标准：Given-When-Then 格式 | 验收标准确认 |
| **UT** | `backend/tests/unit/` | 单元测试 | 单测 |
| **IT** | `backend/tests/integration/` | 集成测试 | 接口测试 |

---

## 三、核心工作流

```
PRD → Scenarios → Architecture(TDS) → ATDD → TDD(RED) → TDD(GREEN) → Refactor → UT → IT → Sign-off
```

### 阶段详解

| 阶段 | 输入 | 输出 | 工具 |
|------|------|------|------|
| **Architecture** | PRD + Scenarios | TDS 技术设计文档 | - |
| **ATDD** | TDS + 用户旅程 | Given-When-Then 验收标准 | Gherkin |
| **TDD RED** | ATDD Scenario | 失败的测试用例 | pytest |
| **TDD GREEN** | 失败的测试 | 最简实现 | pytest |
| **Refactor** | 通过的测试 | 重构代码 | ruff/radon |
| **UT** | 实现代码 | 单元测试通过 | pytest |
| **IT** | UT | 集成测试通过 | pytest |
| **Sign-off** | IT | PR 提交 | pr-gate |

---

## 四、触发条件

- 用户提供设计方案、设计稿、架构文档时
- 用户说"基于这个方案"、"按 Harness 方式"、"ATDD 开发"、"AD-TDD"
- 新增模块 / 修改核心业务逻辑

---

## Phase 0：文档定位确认

在开始实施前，确认当前模块在文档体系中的位置：

| 上游文档 | 本阶段任务 | 下游产出 |
|---------|-----------|---------|
| `docs/PRD/Selfwell-PRD-V1.1.md` | 提取 FR 编号 | → TDS FR 追溯 |
| `docs/scenarios/S*.md` | 提取用户旅程 | → ATDD 场景 |
| `docs/spec/TDS-M*.md`（如已存在） | 读取现有设计 | → 实施依据 |
| `docs/harness/atdd/TDS-M*-AC.md`（如已存在） | 读取已有 AC | → 跳过或补充 |

---

## Phase 1：Architecture — 生成 TDS 技术设计文档

读取用户提供的设计方案，生成 `docs/spec/TDS-<编号>-<标题>.md`。

详见 [TDS-TEMPLATE.md](TDS-TEMPLATE.md) 模板。

> **强约束（必读）**：本项目 TDS 还**必须**复用 [docs/spec/SPEC-HEADER-TEMPLATE.md](../../../docs/spec/SPEC-HEADER-TEMPLATE.md) 的"模板内容"小节（强关联真源表 + 12 项可落地性自检）。Cursor agent 在改任何 `docs/spec/TDS-*.md` 前，先 Read 该模板；提交前必须跑其"提交前必跑命令"全部 grep 通过。

关键约束：
- 每个 Phase/Stage 必须有明确的验收标准（Acceptance Criteria）
- **每条 FR 至少 1 条 Gherkin ATDD，含 Given/When/Then；AC 内字段名/枚举值必须能映射到 openapi.yaml / data-dictionary / yaml 真源（与 SPEC-HEADER-TEMPLATE §1 "FR 可测" / §2 "数据契约" / §3 "API 契约" 对齐）**
- 全量测试场景必须覆盖：正常路径、边界条件、异常路径
- 明确标注哪些是 Smoke Test、哪些是 Full Regression

---

## Phase 2：ATDD — 生成验收标准

在 TDS 生成后，**同步生成**对应的 ATDD 文件 `docs/harness/atdd/TDS-<编号>-AC.md`。

### ATDD 格式要求

- 使用 Gherkin 语言（Given-When-Then）
- 每个 FR 对应至少 1 个 Scenario
- Scenario 必须包含：前置条件（Given）、操作步骤（When）、预期结果（Then）
- 字段名/枚举值必须与 TDS 中的 openapi.yaml / data-dictionary 对齐

### ATDD 文件命名

`TDS-<编号>-AC.md`（AC = Acceptance Criteria）

### 示例结构

```markdown
# TDS-M1: 微信登录 - 验收标准

## Feature: 微信 OAuth 登录

### Scenario: 新用户首次登录
```gherkin
Given 用户已打开 Selfwell 小程序
And 用户未登录（无有效 JWT）
When 用户点击"微信一键登录"
Then 系统调用 wx.login() 获取 code
And 系统 POST /api/v1/auth/wx-login
And 系统跳转至档案填写页面
```

### Scenario: 老用户回访
```gherkin
Given 用户已打开 Selfwell 小程序
And 用户已完成档案填写
When 用户点击"微信一键登录"
Then 系统调用 wx.login() 获取 code
And 系统 POST /api/v1/auth/wx-login
And 系统 JWT 有效期 >= 7 天
And 系统跳转至首页
```
```

---

## Phase 3：TDD — 循环（对每个 ATDD 逐条执行）

对 ATDD 中每个 Scenario，严格按以下顺序执行。实施阶段**必须严格遵循** [coding-standards SKILL.md](../coding-standards.mdc)。

### Step 3.1 — RED：写测试

**真实命令 + 验证（v2026-07-18 修订）**：

```bash
# 1. 进入 backend
cd backend

# 2. 写 1 个最小失败测试（通常只断言 1 个 import + 1 个调用）
#    例如：def test_<feature>_<scenario>_exists(): from app.<x>.<y> import <fn>

# 3. 跑这个测试，期望是 AssertionError，不是 "no test ran"
uv run pytest tests/unit/test_<feature>.py -x --tb=line 2>&1 | tee /tmp/red.log

# 4. 验证 RED 真有效（退出码 1 + 含 AssertionError）
grep -q "FAILED" /tmp/red.log && grep -q "AssertionError" /tmp/red.log \
  && echo "✅ RED 阶段有效（测试因断言失败而 fail）" \
  || { echo "❌ RED 阶段无效：缺 AssertionError 或 FAILED"; exit 1; }

# ⚠️ 期望：exit code = 1（断言失败），不是 5（无测试）
# ⚠️ 期望：log 含 "FAILED" + "AssertionError"，不是 "no tests ran"
```

针对当前 ATDD Scenario，**先写测试**：
- 测试文件放在 `backend/tests/` 对应子目录
- 命名：`test_<功能>_<场景>.py`
- 用 pytest + pytest-asyncio
- 外部 API 调用用 VCR.py 录制 cassette，或 mock
- LLM 调用用 Test Doubles（mock/stub），不调用真实模型
- **每条 RED 验证后立即 git commit `chore(tdd-red): <scenario-id> red阶段测试草稿`**，保留循环节点

### Step 3.2 — GREEN：写实现

在**通过测试的前提下**（即使实现很丑），写最简实现：

- 文件放 `backend/app/` 对应模块
- 遵循 `coding-standards` 目录边界约束（agents/ 仅放图编排，业务逻辑在 nodes/tools/rules/）
- **Agent State 必须继承 TypedDict**（不要用 dict，不要用 Pydantic BaseModel 作为 State）
- 节点签名：`async def node(state: AgentState, runtime: Runtime[AgentContext]) -> dict`
- 节点内禁止直接修改 state，**必须返回状态增量 dict**
- 工具用 `@tool` 装饰器或继承 BaseTool
- 配置从 pydantic-settings 读取，禁止硬编码
- 运行测试：必须 PASS
- **禁止 GREEN 假绿**：
  - ❌ `return []` / `return None` / `return {}` 直接绕过逻辑
  - ❌ `pass` / `NotImplementedError` / `raise TODO`
  - ❌ `try/except: pass` 全吞
  - ❌ magic number 0/1（如 `if score == 1: ...`）绕过 LLM
  - ✅ 必须有真实业务逻辑（即使再简单）
- **每条 GREEN 后立即 git commit `feat(tdd-green): <scenario-id> 最简实现通过`**

### Step 3.3 — REFACTOR

在测试通过后，重构代码消除坏味道。**必须通过 coding-standards 的全部质量门禁**：

| 约束 | 阈值 | 检查工具 |
|------|------|---------|
| 单函数行数 | ≤ 50 行 | `radon -l` |
| 单节点行数 | ≤ 150 行 | `radon -l` |
| 圈复杂度 | 单函数 max A，平均 ≤ B | `radon -a -i A` |
| 嵌套深度 | if ≤ 4 层 | `ruff --select=PLR1702` |
| 参数数量 | ≤ 5 个 | `ruff --select=PLR0913` |

重构时同步更新 docstring 和日志。测试必须全程保持 PASS。

### Step 3.4：迭代下一个验收标准

重复 Step 3.1 → 3.2 → 3.3，直到 ATDD 中所有 Scenario 全部实现。

---

## Phase 4：UT + IT — 全量回归测试

每个 Phase 完成后，**必须执行完整测试套件**：

```bash
cd backend
uv run pytest tests/unit -x -q
uv run pytest tests/integration -x -q
uv run pytest tests/e2e -x -q
uv run pytest tests/smoke -x -q
```

覆盖率门槛：

| 模块 | 门槛 |
|------|------|
| rules/ | ≥ 90% |
| agents/ middleware/ | ≥ 80% |
| tools/ | ≥ 70% |
| 整体 | ≥ 60% |

如果测试失败 → 回到 Phase 3，对应节点修复
如果覆盖率不达标 → 补充缺失测试用例
**必须所有测试 PASS + 覆盖率达标，才允许下一步**

---

## Phase 5：AI 自审（提交前强制检查）

> **v2026-07-18 修订**：本节原引用"coding-standards SKILL.md 的 Step 1-8 自审执行流程"是**虚假引用**
> （coding-standards 实际未定义 Step 1-8）。本节已重写为**真实可执行**的 7 项自审步骤。

**必须执行**下列 7 步，每一步设硬卡。任意 FAIL → 不允许进入 Phase 6：

| # | 步骤 | 命令 | 失败处理 |
|---|------|------|---------|
| 1 | format 校验 | `uv run ruff format --check .` | FAIL → 跑 `ruff format .`（本地可修） |
| 2 | lint | `uv run ruff check . --fix`（**自审阶段允许自动修**，与 verifier 区别） | FAIL → 修 |
| 3 | 类型 | `uv run mypy --strict app/` | FAIL → 修 |
| 4 | 单元测试 | `uv run pytest tests/unit -x -q` | FAIL → 回到 Phase 3.2 |
| 5 | 集成测试 | `uv run pytest tests/integration -x -q` | FAIL → 回到 Phase 3.2 |
| 6 | 覆盖率 | `uv run pytest --cov=app --cov-fail-under=60` | FAIL → 补测试 |
| 7 | prompt 改动（如有） | `python -m eval.runner --mode pr` | FAIL → 调 prompt 或回滚 |

**本 7 步与 L0-L6 映射**（2026-07-19 新增，避免编号漂移）：

| 自审步 | 对应 L 级别 | 真源 |
|-------|-----------|------|
| 1 format 校验 | L1（ruff format） | `.cursor/rules/l0-l6-gates.mdc` §一 L1 |
| 2 lint | L4a（ruff 安全规则） | `.cursor/rules/l0-l6-gates.mdc` §一 L4a |
| 3 类型 | L2（mypy strict） | `.cursor/rules/l0-l6-gates.mdc` §一 L2 |
| 4 单元测试 | L3（unit 子集） | `.cursor/rules/l0-l6-gates.mdc` §一 L3 |
| 5 集成测试 | L3（integration 子集） | `.cursor/rules/l0-l6-gates.mdc` §一 L3 |
| 6 覆盖率 | L6（≥ 60%） | `.cursor/rules/l0-l6-gates.mdc` §一 L6 |
| 7 prompt 改动 | **R-4 Eval Runner**（非 L0-L6） | `.cursor/rules/l0-l6-gates.mdc` §三 + `.cursor/skills/golden-set/SKILL.md` §5 |

**禁止跳过任一项**。与 coding-standards 的关系：

- **本 skill 是执行者**——跑命令
- **`l0-l6-gates.mdc` 是规则定义**——定义命令与阈值

正确引用链：`.cursor/rules/l0-l6-gates.mdc` §十三（14 条）+ 本 skill Phase 5（7 步执行）= 真实可跑的自审。

### 自审报告输出格式

```markdown
## Self-Review 报告（v2026-07-18 新格式）

| # | 步骤 | 结果 | 详情 |
|---|------|------|------|
| 1 | ruff format | ✅ / ❌ | <详情> |
| 2 | ruff check | ✅ / ❌ <N 个修复> | <详情> |
| 3 | mypy --strict | ✅ / ❌ <N 个错误> | <详情> |
| 4 | pytest unit | ✅ / ❌ <N 个失败> | <详情> |
| 5 | pytest integration | ✅ / ❌ <N 个失败> | <详情> |
| 6 | coverage --cov-fail-under=60 | ✅ / ❌ <X% ≥ 60%> | <详情> |
| 7 | eval runner (if prompt) | ✅ / ❌ baseline 跌幅 ≤ 5% | <详情> |

**结论**：✅ PASS（可以 commit）/ ❌ FAIL（必须修复）
```

---

## Phase 6：Sign-off — Git Commit

必须满足以下全部条件才允许 commit：
- TDS 技术设计文档已生成（或已更新）
- ATDD 验收标准已生成（或已更新）
- 所有 ATDD Scenario 已实现
- 全量回归测试 PASS
- 覆盖率达标
- **通过 coding-standards 质量门禁（L0-L6 + AI 自审报告 PASS）**
- commit message 符合 Conventional Commits：`type(scope): subject`（中文 ≤ 30 字）

Commit 格式示例：
```
feat(agent): 实现枚举值澄清 HITL 中断机制

feat(nodes): 新增 process_node 节点

fix(agents): 修复追问上下文丢失问题

test(subgraphs): 补充 value_validation_subgraph 全量测试
```

---

## 测试文件命名规范

ATDD 格式要求：
- 每个 ATDD Scenario 对应至少 1 个 pytest 测试文件
- 测试文件命名：`test_<TDS编号>_<场景>.py`
- 每个 Scenario 内的 Given-When-Then 对应 1 个或多个 test function

| 层级 | 路径 | 命名 |
|------|------|------|
| 单元 | `tests/unit/` | `test_<模块>_<场景>.py` |
| 集成 | `tests/integration/` | `test_<模块>_<交互场景>.py` |
| E2E | `tests/e2e/` | `test_<流程名>.py` |
| Smoke | `tests/smoke/` | `test_<功能名>.py` |
| Playwright | `tests/smoke_playwright/` | `test_<页面>_<操作>.py` |

---

## 与其他 Skill 的边界

| 阶段 | 主用 Skill | 配合 Skill |
|------|-----------|------------|
| Architecture (TDS) | 本 skill（ad-tdd） | `pr-gate`（FR 关联） |
| ATDD 生成 | 本 skill（ad-tdd） | `golden-set`（Prompt 相关场景） |
| TDD RED | 本 skill（ad-tdd） | ATDD 提供场景 |
| TDD GREEN | 本 skill（ad-tdd） | `coding-standards` 提供编码规范 |
| 跑分 / 回归 | - | `golden-set`（Prompt 改动） / `pr-gate`（PR 提交流） |

> 编码规范、复杂度阈值、质量门禁、自审流程的**规则定义**全部以 [coding-standards.mdc](../coding-standards.mdc) 为唯一真源。
>
> **真实执行命令**以本 skill 的 Phase 3 / Phase 4 / Phase 5 表格为准。
>
> **V2 集成（W4 接入）**：ad-tdd 是 Harness 流水线 `04-ATDD / 06-CODE / 07-VERIFY` 三个 phase 的开发指引，**前置** `03-PRE_MORTEM`（5 评审串行）+ `05-PLAN`（实施计划）。
> **不替代** Harness：PR-Gate、Deploy、Regression、Sign-off 在 Phase 6 / ad-tdd 之外。

---

## 参考文档

- TDS 文档模板：[TDS-TEMPLATE.md](TDS-TEMPLATE.md)
- ATDD 验收标准格式：见上方 Phase 2 示例
- TDD 工作流详解：[TDD-WORKFLOW.md](TDD-WORKFLOW.md)
- **项目编码规范 & AI 自审流程（唯一真源）**：[coding-standards.mdc](../coding-standards.mdc)
- PR 合入检查：`.cursor/skills/pr-gate/SKILL.md`
- Golden Set 维护：`.cursor/skills/golden-set/SKILL.md`
- ATDD 库：`docs/harness/atdd/`
- 入口规则：`.cursor/rules/`