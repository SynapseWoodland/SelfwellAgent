---
name: pr-gate-human
description: >
  PR 守门 skill（Human-Only 部分）。当创建 PR、提交流前、或收到 PR review 评论时触发。
  CI 层强制检查见 .github/workflows/pr-gate-ci.yml（真 workflow）+ .cursor/skills/pr-gate-ci/SKILL.md。
  本 skill 仅负责人类视角的提醒与边界说明，不执行任何 CI 检查。
disable-model-invocation: false
---

# PR Gate — Human-Only 检查

> **触发本 skill**：用户在 Cursor 主会话说"创建 PR"、"提交代码"、"提个 MR"、"帮我检查这个改动"。
>
> **不做**：不执行 shell 命令、不修改文件、不直接合并 PR——这些都是 CI（`pr-gate-ci.yml`）和开发者的工作。

## 触发条件

- 用户说"创建 PR"、"提交代码"、"提个 MR"、"帮我检查这个改动"
- 用户修改了 `agents/harness/` / `harness/` / `.cursor/skills/` 下的 Harness 相关文件
- 用户修改了 `.github/workflows/` 下的 CI 配置

## 检查清单（Human-Only）

### 1. FR 关联提醒

检查本次改动关联了哪些 FR：
- 如果没有 FR 编号 → 输出提醒，要求在 PR description 加 `FR-<MODULE>-<NUM>`
- 如果有关联 → 在 PR description 中列出，并提醒豁免前缀（chore/deps/, docs/readme/, ci/workflow/）

### 2. 覆盖率提醒（模块级）

提醒开发者检查改动模块的覆盖率（**真源**：`.cursor/rules/l0-l6-gates.mdc` §二 L6 + §十八）：

| 模块 | 阈值 | 命令 |
|------|------|------|
| `rules/` | ≥ 90% | `pytest tests/unit -k rules --cov-fail-under=90` |
| `agents/` `middleware/` | ≥ 80% | `pytest tests/unit -k agents --cov-fail-under=80` |
| `tools/` | ≥ 70% | `pytest tests/unit -k tools --cov-fail-under=70` |
| **整体** | **≥ 60%** | `pytest --cov=app --cov-fail-under=60` |

> ⚠️ 提醒开发者：**CI 硬卡 ≥ 60%**，模块级阈值是建议目标，不是 CI 拦截项。

### 3. CI 状态检查

提醒开发者跑完本地 L0-L6 后再推（**真源**：`.cursor/rules/l0-l6-gates.mdc`）：

```bash
# 本地预跑（提交前）
cd backend && uv run ruff check . --fix && uv run ruff format --check .
uv run mypy --strict backend/app/
uv run pytest backend/tests/unit -x -q
```

## 输出格式

完成检查后输出结构化总结：

```markdown
## PR Gate Human-Only 检查

### 关联项
- FR 编号：FR-XXX-XX（如有）
- 相关 ADR：ADR-XXXX（如有）
- 相关 ATDD：ATDD-XXX（如有）

### 自检清单
- [ ] 本地 ruff / mypy / pytest 全 PASS
- [ ] PR description 含 FR 编号
- [ ] 改动模块覆盖率达标
- [ ] 无 L0-L6 漂移（详见 .cursor/rules/l0-l6-gates.mdc）

### CI 真 workflow 卡口（自动跑，开发者无需操作）
- Gate 1 commitlint / Gate 2 fr-required / Gate 3 atdd-required / Gate 4 adr-conflict
- Gate 5 coverage / Gate 6 pr-size / Gate 7 l0-l6-consistency

详见 .github/workflows/pr-gate-ci.yml
```

## 边界说明（CI vs Human）

| 检查项 | CI 层（自动） | Human 层（本 skill） |
|--------|--------------|---------------------|
| Commit 格式 | ✅ `pr-gate-ci.yml` Gate 1 | — |
| FR 编号 | ✅ `pr-gate-ci.yml` Gate 2 | 关联性提醒 |
| ATDD 存在 | ✅ `pr-gate-ci.yml` Gate 3 | — |
| ADR 冲突 | ✅ `pr-gate-ci.yml` Gate 4 | — |
| 覆盖率 | ✅ `pr-gate-ci.yml` Gate 5 | 达标提醒（模块级） |
| PR 大小 | ✅ `pr-gate-ci.yml` Gate 6 | — |
| L0-L6 一致性 | ✅ `pr-gate-ci.yml` Gate 7 | — |

> **2026-07-19 W4 P4 §5.1.3 修订**：本 skill 从 `.cursor/skills/pr-gate/SKILL.md` 重命名 + 精简——
> - 删除"CI 层检查见 pr-gate.yml"（该文件已重命名为 `pr-gate-LEGACY.md`，不再是 workflow）
> - 删除 7 项卡口的"CI 层 ✅"列（改指 pr-gate-ci workflow）
> - 模块级覆盖率阈值改为"建议目标"（强调 CI 硬卡只检整体 ≥ 60%）