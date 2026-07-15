---
name: sdd-tdd
description: >
  告知cursor agent实施计划，cursor agent开始编写代码时触发。
  自动生成 SPEC 实施文档，编写全量测试用例，驱动红-绿-重构，最后通过全量回归测试 + coding-standards 质量门禁才允许提交。
  工作流：SDD → SPEC → 红（写测试） → 绿（写实现） → 重构 → 全量回归 OK → AI 自审 PASS → git commit。
  代码实施阶段必须严格遵循 coding-standards SKILL.md（L0-L6 质量门禁）。
disable-model-invocation: false
---

# SDD → TDD 开发流

## 触发条件

- 用户提供设计方案、设计稿、架构文档时
- 用户说"基于这个方案"、"按 SDD 方式"、"TDD 开发"

## 核心工作流

```
SDD → SPEC 实施文档 → 写测试（RED） → 写实现（GREEN） → 全量回归 → git commit
```

---

## Phase 1：生成 SPEC 实施文档

读取用户提供的设计方案，生成 `.cursor/specs/SPEC-<编号>-<标题>.md`。

详见 [SPEC-TEMPLATE.md](SPEC-TEMPLATE.md) 模板。

> **强约束（必读）**：本项目 SPEC 还**必须**复用 [docs/spec/SPEC-HEADER-TEMPLATE.md](../../../docs/spec/SPEC-HEADER-TEMPLATE.md) 的"模板内容"小节（强关联真源表 + 12 项可落地性自检）。Cursor agent 在改任何 `docs/spec/SPEC-*.md` 前，先 Read 该模板；提交前必须跑其"提交前必跑命令"全部 grep 通过。

关键约束：
- 每个 Phase/Stage 必须有明确的验收标准（Acceptance Criteria）
- **每条 FR 至少 1 条 Gherkin AC，含 Given/When/Then；AC 内字段名/枚举值必须能映射到 openapi.yaml / data-dictionary / yaml 真源（与 SPEC-HEADER-TEMPLATE §1 "FR 可测" / §2 "数据契约" / §3 "API 契约" 对齐）**
- 全量测试场景必须覆盖：正常路径、边界条件、异常路径
- 明确标注哪些是 Smoke Test、哪些是 Full Regression

---

## Phase 2：TDD 循环（对每个验收标准逐条执行）

对 SPEC 中每个验收标准，严格按以下顺序执行。实施阶段**必须严格遵循** [coding-standards SKILL.md](../coding-standards/SKILL.md)。

### Step 2.1 — RED：写测试

```bash
cd backend
uv run pytest tests/unit -x -q --tb=short
```

针对当前验收标准，**先写测试**：
- 测试文件放在 `backend/tests/` 对应子目录
- 命名：`test_<功能>_<场景>.py`
- 用 pytest + pytest-asyncio
- 外部 API 调用用 VCR.py 录制 cassette，或 mock
- LLM 调用用 Test Doubles（mock/stub），不调用真实模型
- 运行测试：**必须 FAIL**（因为实现不存在）

### Step 2.2 — GREEN：写实现

在**通过测试的前提下**（即使实现很丑），写最简实现：

- 文件放 `backend/app/` 对应模块
- 遵循 `coding-standards` 目录边界约束（agents/ 仅放图编排，业务逻辑在 nodes/tools/rules/）
- **Agent State 必须继承 TypedDict**（不要用 dict，不要用 Pydantic BaseModel 作为 State）
- 节点签名：`async def node(state: AgentState, runtime: Runtime[AgentContext]) -> dict`
- 节点内禁止直接修改 state，**必须返回状态增量 dict**
- 工具用 `@tool` 装饰器或继承 BaseTool
- 配置从 pydantic-settings 读取，禁止硬编码
- 运行测试：必须 PASS

### Step 2.3 — REFACTOR

在测试通过后，重构代码消除坏味道。**必须通过 coding-standards 的全部质量门禁**：

| 约束 | 阈值               | 检查工具 |
|------|------------------|---------|
| 单函数行数 | ≤ 50 行           | `radon -l` |
| 单节点行数 | ≤ 150 行          | `radon -l` |
| 圈复杂度 | 单函数 max A，平均 ≤ B | `radon -a -i A` |
| 嵌套深度 | if ≤ 4 层         | `ruff --select=PLR1702` |
| 参数数量 | ≤ 5 个            | `ruff --select=PLR0913` |

重构时同步更新 docstring 和日志。测试必须全程保持 PASS。

### Step 2.4：迭代下一个验收标准

重复 Step 2.1 → 2.2 → 2.3，直到 SPEC 中所有验收标准全部实现。

---

## Phase 3：全量回归测试

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

如果测试失败 → 回到 Phase 2，对应节点修复
如果覆盖率不达标 → 补充缺失测试用例
**必须所有测试 PASS + 覆盖率达标，才允许下一步**

---

## Phase 4：AI 自审（提交前强制检查）

**必须执行** [coding-standards SKILL.md](../coding-standards/SKILL.md) 中的 AI 自审执行流程（Step 1-8）。禁止跳过任何 FAIL 项。

快速失败原则：FAIL 必须立即修复，WARN 记录在 PR 描述中。

自审报告输出后，才允许进入 Phase 5。

---

## Phase 5：Git Commit

必须满足以下全部条件才允许 commit：
- SPEC 实施文档已生成
- 所有验收标准已实现
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

| 层级 | 路径 | 命名 |
|------|------|------|
| 单元 | `tests/unit/` | `test_<模块>_<场景>.py` |
| 集成 | `tests/integration/` | `test_<模块>_<交互场景>.py` |
| E2E | `tests/e2e/` | `test_<流程名>.py` |
| Smoke | `tests/smoke/` | `test_<功能名>.py` |
| Playwright | `tests/smoke_playwright/` | `test_<页面>_<操作>.py` |

## 与其他 Skill 的边界

| 阶段 | 主用 Skill | 配合 Skill |
|------|-----------|------------|
| 写测试（RED）| 本 skill（sdd-tdd） | - |
| 写实现（GREEN）| 本 skill（sdd-tdd） | `coding-standards` 提供编码规范 |
| 跑分 / 回归 | - | `golden-set`（Prompt 改动） / `pr-gate`（PR 提交流） |

> 编码规范、复杂度阈值、质量门禁、自审流程**全部**以 [coding-standards/SKILL.md](../coding-standards/SKILL.md) 为唯一真源，本 skill 不复制定义。

---

## 参考文档

- SPEC 文档模板：[SPEC-TEMPLATE.md](SPEC-TEMPLATE.md)
- TDD 工作流详解：[TDD-WORKFLOW.md](TDD-WORKFLOW.md)
- **项目编码规范 & AI 自审流程（唯一真源）**：[coding-standards/SKILL.md](../coding-standards/SKILL.md)
- PR 合入检查：`.cursor/skills/pr-gate/SKILL.md`
- Golden Set 维护：`.cursor/skills/golden-set/SKILL.md`
- 入口规则：`.cursorrules`
