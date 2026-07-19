---
name: pr-gate-ci
description: >
  PR Gate CI 层 skill。描述 .github/workflows/pr-gate-ci.yml（真 GitHub Actions workflow）的 7 项硬卡口实现。
  本 skill 是给开发者和 reviewer 看的 CI 实现说明，不是 CI 检查本身——CI 检查由 GitHub Actions 自动执行。
disable-model-invocation: false
---

# PR Gate — CI 层描述

> **触发本 skill**：开发者想了解"PR Gate 卡口具体怎么跑"、"为什么我的 PR 被拒"、或 reviewer 想检查 PR-Gate CI 实现完整性时。
>
> **不做**：不执行 CI、不修改 workflow、不直接接受 PR——GitHub Actions 自动执行。

## 真 workflow 真源

**文件**：`.github/workflows/pr-gate-ci.yml`（**真 GitHub Actions workflow**，由 GitHub 自动执行）

> ⚠️ **历史**：本工作流从 `.github/workflows/pr-gate.yml`（原 markdown 文档）提取。**2026-07-19 W4 P4 §5.1.2 架构师重构**：原文件是 markdown，GitHub 永远不会执行其中的 YAML 块——这是项目历史最大的潜在风险之一。

## 7 项硬卡口

| Gate | 名称 | 实现 | 失败后果 |
|------|------|------|----------|
| 1 | Commit 格式 | `wagoid/commitlint-github-action@v5` + `.commitlintrc.json` | commitlint 报错 → CI red |
| 2 | FR 编号关联 | bash 内联 + 豁免前缀检测（chore/deps/, docs/readme/, ci/workflow/） | PR title/body 无 FR 编号 → CI red |
| 3 | ATDD 存在性 | `.github/scripts/check_atdd.sh` | 缺 ATDD-XXX.md → CI red |
| 4 | ADR 冲突 | `.github/scripts/check_adr.sh` | 改 freeze ADR / 新增 ADR 缺字段 → CI red |
| 5 | 覆盖率硬卡 | `pytest --cov=backend/app --cov-fail-under=60` | < 60% → CI red |
| 6 | PR 大小 | bash 计算 `git diff --shortstat` 行数 | > 600 行 → CI red |
| 7 | L0-L6 一致性 | bash 扫非白名单 .md 文件 | 重写 L0-L6 表格 / 含 ≥ 80% 旧阈值 / Eval Runner 错位 → CI red |

总闸 job `pr-gate-summary` 检查所有 Gate 状态，任一非 `success` → 拒绝合入。

## 触发条件

```yaml
"on":
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]
```

## 与其他 workflow 的关系

| workflow | 职责 |
|----------|------|
| `backend-ci.yml` | L0-L4 跑分（ruff / mypy / pytest / Golden Set / OpenAPI / ack-pool）+ L5 grep 12 条 |
| `harness-ci.yml` | Harness 4 条 grep 兜底（R-2 红线等） |
| **`pr-gate-ci.yml`** | **本工作流**——PR 业务守门 7 项卡口 |

**串联顺序**（必须都 PASS）：
1. `backend-ci.yml` 跑 L0-L4 + L5 → 任一 FAIL → PR 拒绝
2. `harness-ci.yml` 跑 4 条 grep → FAIL → PR 拒绝
3. `pr-gate-ci.yml` 跑 7 项卡口 → 任一 FAIL → PR 拒绝

## 7 项卡口详细说明

### Gate 1: Commit 格式

**配置**：`.commitlintrc.json`

```json
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "type-enum": [2, "always", ["feat", "fix", "refactor", "test", "docs", "chore", "perf"]],
    "header-max-length": [2, "always", 60],
    "subject-case": [2, "always", "lower-case"]
  }
}
```

**正例**：`feat(plan): 实现计划回退按钮`
**反例**：`Update stuff`、`Fix bug`、`feat: `（缺 scope）

### Gate 2: FR 编号关联

**规则**：
- PR title 或 body 必须含 `FR-<MODULE>-<NUM>`（例：`FR-PLAN-01`）
- 豁免前缀（自动跳过）：`chore(deps):`、`docs(readme):`、`ci(workflow):`
- 强制豁免：commit body 加 `BREAKING-CHANGE-FR-EXEMPT: <reason>`

**反例**：`Update stuff` 标题 + `随便改改` body → CI red

### Gate 3: ATDD 验收测试存在性

**脚本**：`.github/scripts/check_atdd.sh`

**规则**：PR 修改 `backend/app/<module>/` 时必须存在 `harness/atdd/ATDD-<MODULE>-*.md`

**当前豁免**：若 `harness/atdd/` 目录不存在，warning 而非 red（待 W4 P4 §5.3 pilot FR 落地后启用严格检查）

### Gate 4: ADR 冲突检查

**脚本**：`.github/scripts/check_adr.sh`

**规则**：
1. 改 freeze ADR（顶部 `freeze: true`）必须 PR 标题含 `ADR-AMENDMENT`
2. 新增 ADR 必须含 4 字段：`status` / `date` / `decider` / `consequences`

**当前豁免**：仅 docs/adr/ + harness/ + .cursor/ + .github/ 维护类改动不检查

### Gate 5: 覆盖率硬卡 ≥ 60%

```bash
uv run pytest backend/tests/ \
  --cov=backend/app \
  --cov-report=term-missing \
  --cov-fail-under=60
```

> ⚠️ CI 只硬卡 **整体 ≥ 60%**。模块级阈值（rules ≥ 90% / agents ≥ 80% / tools ≥ 70%）是建议目标，由 human-only skill 提醒。

### Gate 6: PR Diff 大小 ≤ 600 行

```bash
LINES=$(git diff --shortstat origin/${{ github.base_ref }}...HEAD | awk '{print $4 + $6}')
if [ "$LINES" -gt 600 ]; then exit 1; fi
```

**说明**：CI 给 600 行硬上限（比 skill 文档给的 300 翻倍），为开发者留 buffer。

### Gate 7: L0-L6 文档一致性

**白名单**（重写 L0-L6 表格是被允许的）：
- `.cursor/rules/l0-l6-gates.mdc`（**唯一真源 + alwaysApply**）
- `harness/L0-L6-TRUTH.md`（摘要）
- `harness/L0-L6-AUDIT-2026-07-19.md`（审计报告）
- `harness/checklist.md`（修复 checklist）
- `.github/workflows/pr-gate-LEGACY.md`（历史 markdown）
- `.github/workflows/pr-gate-ci.yml`（本工作流）
- `.github/workflows/backend-ci.yml`（CI 含 L0-L4 步骤注释）

**检测 3 类违规**：
1. 非白名单 .md 文件含 ≥ 6 行 `| L[0-6] |` 表格行
2. 含过期阈值 `coverage >= 80%` / `覆盖率 >= 80%`
3. L2 = Eval Runner 错位

## 失败后如何修复

| Gate 失败 | 修复指引 |
|-----------|----------|
| Gate 1 commitlint | 改 commit message 格式：`feat(scope): subject` |
| Gate 2 FR 编号 | PR title/body 加 `FR-<MODULE>-<NUM>` 或加豁免前缀 |
| Gate 3 ATDD | 新建 `harness/atdd/ATDD-<MODULE>-<SEQ>.md` |
| Gate 4 ADR 冲突 | 标题加 `ADR-AMENDMENT` 前缀 或 解除 freeze |
| Gate 5 覆盖率 | 补 unit test 达到 60% |
| Gate 6 PR 大小 | 拆分 PR（每个 PR 关联 1 个 FR） |
| Gate 7 L0-L6 一致性 | 删除重写的表格 / 改 `≥ 60%` / 删除 Eval Runner 错位 |

## 参考

- 真源 workflow：`.github/workflows/pr-gate-ci.yml`
- 历史规范（已冻结）：`.github/workflows/pr-gate-LEGACY.md`
- Human-Only 视角：`.cursor/skills/pr-gate-human/SKILL.md`
- L0-L6 真源：`.cursor/rules/l0-l6-gates.mdc`
- 5 条红线：`.cursor/rules/project-prohibitions.mdc`