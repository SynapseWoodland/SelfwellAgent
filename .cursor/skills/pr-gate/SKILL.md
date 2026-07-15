---
name: pr-gate
description: >
  PR 守门 skill。当创建 PR、提交流前、或收到 PR review 评论时触发。
  自动检查：FR 关联性、验收测试存在性、ADR 冲突、覆盖率门槛、CI 状态。
  用于确保每个 PR 符合 `coding-standards/SKILL.md` 的工程规范。
disable-model-invocation: false
---

# PR Gate — 自动守门 Skill

## 触发条件

- 用户说"创建 PR"、"提交代码"、"提个 MR"、"帮我检查这个改动"
- 或主动触发：当 AI 完成一段代码后

## 检查清单（逐项执行）

### 1. FR 关联检查

检查本次改动关联了哪些 FR（功能需求编号）：

- 在 PR description 或 commit message 中查找 `FR-XXX-XX` 格式
- 如果**没有** FR 编号 → 输出警告：
  > ⚠️ 未找到 FR 编号。本次改动应关联至少 1 个 FR（格式：`FR-<模块>-<编号>`），例如 `FR-PLAN-01`、`FR-SUB-01`。
- 如果有关联 → 在 PR description 中列出所有关联的 FR

### 2. 验收测试检查

检查是否存在对应的验收测试文件：

- 格式：`tests/acceptance/fr/FR-XXX-XX.feature`
- 如果 FR 关联了但 feature 不存在 → 输出警告：
  > ⚠️ FR `FR-XXX-XX` 关联了但未找到对应验收测试。请在 `tests/acceptance/fr/FR-XXX-XX.feature` 创建 Gherkin Scenario。

### 3. ADR 冲突检查

检查本次改动是否与已有 ADR 冲突：

- 读取 `docs/adr/` 下所有 `.md` 文件的标题
- 检查代码改动是否违反了 ADR 声明（例如：把 SQLite 换成 Postgres → 检查 ADR-0002）
- 如果发现冲突 → 输出：
  > 🔴 ADR 冲突：本次改动与 `ADR-XXXX-<title>` 冲突。请先修改 ADR 或调整方案。

### 4. 覆盖率门槛检查

> **统一真源**：覆盖率门槛以 `coding-standards/SKILL.md` 的"测试规范"章节为准（`rules >= 90%`、`agents/middleware >= 80%`、`tools >= 70%`、整体 `>= 60%`）。本 skill 不重复定义。

检查改动的模块是否达到覆盖率门槛：

| 模块 | 门槛 |
| --- | --- |
| `agents/` `middleware/` `rules/` | ≥ 80% |
| `tools/` | ≥ 70% |
| 整体 | ≥ 60% |

- 如果改动的文件在低覆盖率模块 → 输出：
  > ⚠️ 改动涉及 `XXX/` 模块，当前覆盖率可能不达标。请确保新增代码有对应的单测。

### 5. CI 状态检查

如果 PR 已创建，检查 CI 状态：

- 查看 `.github/workflows/ci.yml` 是否会触发
- 检查是否包含 `ruff check`、`mypy --strict`、`pytest tests/unit` 三件套
- 如果 CI 流程缺失关键步骤 → 输出：
  > ⚠️ CI 流程可能缺少必要步骤。请确认 ci.yml 包含 ruff + mypy + pytest。

### 6. Commit 规范检查

检查 commit message 是否符合 Conventional Commits：

- 格式：`<type>(<scope>): <subject>`（中文，≤30 字，祈使句）
- type：feat | fix | refactor | test | docs | chore | perf
- scope：agents | middleware | tools | rules | api | frontend | i18n | ci
- 如果不符合 → 输出：
  > ⚠️ Commit 格式不规范。推荐：`type(scope): subject`（中文，≤30 字）。

### 7. PR Diff 大小检查

检查本次改动的 diff 行数：

- **单 PR diff ≤ 300 行**（不含 fixture / cassette / lockfile）
- 如果超过 → 输出：
  > ⚠️ PR diff 超过 300 行。请拆分为多个小 PR（推荐每个 PR 关联 1 个 FR）。

## 输出格式

完成所有检查后，输出结构化总结：

```
## PR Gate 检查结果

| 检查项 | 状态 |
| --- | --- |
| FR 关联 | ✅ FR-XXX-XX / ⚠️ 未找到 |
| 验收测试 | ✅ 存在 / ⚠️ 缺失 |
| ADR 冲突 | ✅ 无冲突 / 🔴 冲突 |
| 覆盖率 | ✅ 可能达标 / ⚠️ 可能不达标 |
| CI 状态 | ✅ 完整 / ⚠️ 可能缺失 |
| Commit 格式 | ✅ 规范 / ⚠️ 不规范 |
| PR 大小 | ✅ ≤300行 / ⚠️ 超 300 行 |

**结论**：✅ 可以合并 / ⚠️ 请修复上述问题后再合并
```

## 触发示例

- "帮我检查这个 PR 的改动是否符合规范"
- "这个 commit 怎么写"
- "创建 PR 需要什么"
- AI 主动触发（代码编写完成后）

## 与其他 Skill 的边界

| Skill | 职责 | 本 skill 不做什么 |
|-------|------|------------------|
| `coding-standards/SKILL.md` | 代码质量自审（L0-L6 门禁） | 不复查 ruff/mypy/pytest |
| `golden-set/SKILL.md` | Prompt 回归 + Eval 跑分 | 不跑 Golden Set |
| `sdd-tdd/SKILL.md` | SDD→TDD 开发流 | 不驱动 TDD 循环 |
