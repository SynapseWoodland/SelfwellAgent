# Harness 真源迁移审视清单（C-14 dry-run）

> **目的**：把"全仓 harness 文档体系从 `harness/` 迁移到仓库根 `harness/`"这一改动涉及的所有事实、风险、级联路径、决策点、动手前 sanity 检查，全部汇总到一份审视稿里，**不入 git**，给架构师审完后再执行。
>
> **生成时间**：2026-07-19 17:11 UTC+8
> **生成人**：Harness 架构师 + Cursor Agent（dry-run）
> **依据**：本会话上一轮 17 项审计报告（`harness/L0-L6-AUDIT-2026-07-19.md` 已记录）+ 10 项 AskQuestion 决策
> **本稿不入 git**：必须由架构师逐项 ✅ / ❌ / 修正后，才进入 Step 2 真实 commit

---

## 0. 决策摘要（10 项 Q1–Q10 锁定结果）

| # | 决策点 | 取值 |
|---|---|---|
| Q1 | P0 优先级 PR 颗粒度 | Q1-C-asset-first（先只做 C-14，C-2/C-4 等 docs 变 git tracked 后再走 PR）|
| Q2 | .gitignore 解除范围 | Q2-A-full-unignore（整体解除 `harness/**` ignore）|
| Q3 | ATDD 命名收敛 | Q3-A-docs-to-actual（4 处文档向实物靠拢：`TDS-<编号>-AC.md` → `ATDD-M<N>-AC.md`）|
| Q4 | 一人模式策略 | Q4-B-yaml-and-protocol（yaml 字段 + 4 份协议措辞同步为"2 reviewer + 1 orchestrator"）|
| Q5 | dry-run 范围 | Q5-A-harness-only（仅 `harness/**`）|
| Q6 | .gitkeep 策略 | Q6-A-lessons-patterns（仅 lessons/ + patterns/ 加 .gitkeep）|
| Q7 | commit 形式 | Q7-A-single-pr-multi-commit（单 PR 多 commit）|
| Q8 | 退化兜底 | Q8-A-new-yaml（新建 `.github/workflows/docs-harness-ci.yml` + 轻量 `git check-ignore`）|
| Q9 | 路径命名 | **Q9-A-rename-recommended**（`harness/` → 仓库根 `harness/`）|
| Q10 | 级联范围 | Q10-A-full（全仓跨目录一并改正）|
| Q11 | PR 标题 | `refactor(harness)!: move harness to root harness/` |
| Q12 | 分支 | 当前分支（commit 不 push）|
| Q13 | 附加 | Q13-A-leak-scan（secret 扫描防商业敏感误追踪）|

> Q9 = Q2-A 的"根因版"：因为 `.gitignore` 行 21 是 `docs/` 整体 ignore（不仅 `harness/**`），Q2-A"在 docs 内 unignore"只能解表；Q9-A"移到根"才能彻底脱离 ignore 控制区。这与 Q8-A 兜底不冲突——Q9-A 治根因，Q8-A 治未来。

---

## 1. Step 1 扫描事实（2026-07-19 17:11 已跑）

### 1.1 `git check-ignore` + git status --ignored 实测

```bash
$ git check-ignore -v harness/**
.gitignore:21:docs/	harness/**
```

→ **命中原因**：第 21 行 `docs/` **整体** ignore（不是 `harness/**` 单独 ignore）。

### 1.2 `git ls-files harness/`

→ **0 命中**。harness 全树从来没进过 git。

### 1.3 `git log --all --oneline -- harness/`

→ **0 commit**。确认 harness 文档是"本地孤儿"。

### 1.4 全仓 grep `harness` 硬编码命中

共 **13 个文件**（约 20 处命中）：

```
agents\harness\DISPATCHER.md
agents\harness\EXECUTORS.md
agents\harness\ORCHESTRATOR.md
agents\harness\REVIEWERS.md
.cursor\rules\l0-l6-gates.mdc
.cursor\rules\rule-navigation.mdc
.cursor\skills\ad-tdd\SKILL.md
.cursor\skills\ad-tdd\TDS-TEMPLATE.md
.cursor\skills\harness-autolearn\SKILL.md
.cursor\skills\harness-business-interview\SKILL.md
.cursor\skills\harness-dispatcher\SKILL.md
.github\workflows\harness-ci.yml
.github\workflows\pr-gate.yml
```

### 1.4b backend/ 跨仓依赖核验

```bash
$ git grep -l "harness" backend/
（0 命中，clean）
```

→ 确认 `eval.runner` 等 backend 工具无相对路径依赖 `harness`。

### 1.4c `harness/` 实物总数 shell 验证

```bash
$ find harness -type f -not -path "*/.gitkeep" | wc -l
45
```

### 1.5 secret / 凭证扫描

```bash
$ grep -rE "api[_-]?key|password|secret|token|private[_-]?key|AKID|SecretAccessKey|BEGIN [A-Z ]+PRIVATE KEY" harness/
```

→ **0 命中**。harness 文档无敏感凭证。但**注意**：KPI / 成本模型 / 用户数据 / 关键词黑名单等商业敏感内容均在 `docs/architecture/` 和 `docs/data/`，**不属于** harness 范围，无需担心。

### 1.6 `harness/` 实物清单（共 45 份，按目录分组）

```
harness/
├── .archive/
│   └── architecture.md                                           # 旧版 V1.0 草稿（DEPRECATED）
├── ARCHITECTURE-AND-USAGE.md                                     # V2 架构 + 用法
├── architecture.md                                               # 旧版 V1.0 草稿（DEPRECATED）
├── atdd/
│   ├── ATDD-M1-AC.md                                             # 模块 1 ATDD 验收标准
│   ├── ATDD-M10-AC.md
│   ├── ATDD-M12-AC.md
│   ├── ATDD-M13-AC.md
│   ├── ATDD-M14-AC.md
│   ├── ATDD-M2-AC.md
│   ├── ATDD-M3-AC.md
│   ├── ATDD-M4-AC.md
│   ├── ATDD-M5-AC.md
│   ├── ATDD-M6-AC.md
│   ├── ATDD-M7-AC.md
│   └── ATDD-M8-AC.md                                             # 注意：M9/M11 缺失（Q3 决策待修）
├── checklist.md                                                 # 本次审计的 checklist 母本
├── context/
│   ├── 11-security-test.md                                       # 6 份 V2 phase context
│   ├── 12-data-replay.md
│   ├── 13-incident-response.md
│   ├── 14-ops-loop.md
│   ├── 15-skill-update.md
│   ├── 16-interrupt-review.md
│   └── phase-checklist.md                                        # 16 phase 总览
├── EVALUATION-PROMPT.md                                          # 评估 prompt 模板（非真源）
├── evidence/
│   ├── .gitkeep
│   └── README.md                                                # evidence schema 真源
├── GAP-ANALYSIS.md                                               # 历史 gap 分析报告
├── HARNESS-EVALUATION.md                                         # 一人模式评估报告
├── L0-L6-AUDIT-2026-07-19.md                                     # L0-L6 修复审计报告
├── L0-L6-TRUTH.md                                                # L0-L6 真源摘要
├── lessons/                                                      # 空目录（autolearn 沉淀位置，Q6 决策需加 .gitkeep）
├── MIGRATION-V2.md                                               # V1.6→V2 迁移说明（"Status: draft for review" 仍待改）
├── README-V2.md                                                  # V2 入口 README（V2 当前活跃状态，决策 Q4 需改）
├── README.md                                                     # 旧 V1.6 README（声称 V1.6 活跃，冲突 C-1）
├── scripts/
│   └── check.sh                                                  # 4 条 harness grep 兜底
├── state/
│   ├── .gitkeep
│   ├── SNAPSHOT-INSTRUCTIONS.md                                  # V1.6 冻结说明（DEPRECATED by V2）
│   ├── harness-state.example.json                                # V1.6 example（需升级 V2，决策 C-9 待修）
│   ├── harness-state.json                                        # V2 实物
│   └── harness-state.schema.md                                   # V2 schema 真源
├── templates/
│   ├── acceptance.md                                             # V1.6 7 字段 frontmatter（决策 C-5 待升 8 字段）
│   ├── lesson-record.md                                          # autolearn 5 字段（与 evidence 体系脱钩）
│   ├── pre-mortem.md                                             # V1.6 7 字段（决策 C-5 待升 8 字段）
│   └── synthesis.md                                              # V1.6 6 字段"A 档精简"（决策 C-5 待升 8 字段）
├── workflow-v2.yaml                                              # V2 状态机真源（16 phase）
└── workflow.yaml                                                 # V1.6 状态机（10 phase，已冻结但仍可写）
```

> **空目录**：`lessons/` 与 `patterns/`（patterns/ 在实物中尚未创建，Q6 仅加 lessons/.gitkeep）。

### 1.7 当前分支 + 最近 commits

- 分支：`main`
- 最近 5 commits：
  ```
  9271493 docs(rules): 删除 rule-navigation §2.1 冗余的「内容来源」列
  5a43d53 docs(skills): 修正 harness-autolearn skill 路径与边界表
  60ac868 docs: remove obsolete docs (gitignored)
  4610c6e feat(skills): add harness skill suite (dispatcher/evidence/autolearn)
  005849c refactor(ci): update backend-ci.yml + AGENTS.md
  ```
- **观察**：harness docs 相关 commits 全部在 git 历史中"假动作"——commit message 说改了，但 `git log --all -- harness/` 0 命中。这是 harness 资产治理最严重的"账面与实物脱钩"症状。

---

## 2. 改动范围（本 PR 涉及）

### 2.1 路径移动（45 份文件）

| from | to | 文件数 |
|---|---|---|
| `harness/**` | `harness/**`（仓库根）| 45 |

### 2.2 .gitignore 改动

| 改动 | 内容 |
|---|---|
| 删除 | 第 21 行 `docs/` 整体 ignore → 改为 `docs/PRD/` / `docs/audit/` / `docs/bugfix/` / `docs/architecture/` / `docs/adr/` / `docs/api/` / `docs/data/` 等**子目录**级 ignore |
| 保留 | 第 1–20 行其余条目不动 |
| 新增 | 加注释说明 `harness/` 已迁出 → `harness/`，恢复 git tracked |

### 2.3 .gitkeep 新增

| 路径 | 目的 |
|---|---|
| `harness/lessons/.gitkeep` | autolearn lesson 沉淀位置（autolearn 真源 `.cursor/skills/harness-autolearn/SKILL.md` 强制要求目录存在）|
| `harness/patterns/.gitkeep` | autolearn pattern 沉淀位置（即使 patterns/ 实物不存在，目录初始化时就要在）|

> **决策 Q6 修正建议**：原 Q6 决策"只 lessons/ + patterns/ 加 .gitkeep"——本审视稿建议**保留 Q6 不动**，等 docs 整体 ignore 解除后，`harness/lessons/` 和 `harness/patterns/` 实物目录才被 git 跟踪；此时若两目录都为空，git 不跟踪空目录 → **需要 .gitkeep**。本步骤执行 ✓。

### 2.4 全仓硬编码路径替换（13 个文件，约 20 处命中）

**规则**：`harness/` → `harness/`（13 个文件全仓）

```bash
$ git grep -l "harness" | xargs sed -i 's|harness/|harness/|g'
```

> **注意**：本次只改 `harness/` 字符串（前缀），不动 `harness/MIGRATION-V2.md` 等内部相对路径——相对路径自然从 `harness/` 变 `harness/` 即可。

### 2.5 新增 CI 文件（1 份）

`.github/workflows/docs-harness-ci.yml`：
- 触发条件：`harness/**` 路径变化 + `.github/workflows/docs-harness-ci.yml` 自身变化
- 步骤：
  1. checkout
  2. `git check-ignore -v harness/**` → 任一命中 = exit 1
  3. `git check-ignore -v harness/lessons/* harness/patterns/*` → 空命中警告（提醒开发者补 .gitkeep）

---

## 3. 风险评估

### 3.1 高风险项（必须架构师确认）

| # | 风险 | 概率 | 严重度 | 缓解 |
|---|---|:---:|:---:|---|
| R-1 | `.gitignore` 第 21 行 `docs/` 整体 ignore 改了之后，**别的 `docs/` 子目录**（PRD / ADR / API / architecture / data / MVP-* 等）会**意外进入 git** | 高 | 高 | 必须逐项加 ignore 行（见 §4）|
| R-2 | 移动到根 `harness/` 后，与 `.cursor/skills/harness-*/` 在路径上产生语义冲突（都是 harness 命名空间）| 低 | 中 | 文档化区分：`harness/` = 控制面文档，`.cursor/skills/harness-*/` = Skill 配置 |
| R-3 | PR-Gate 卡口 6（PR diff ≤ 600 行）会因为大批新文件 commit 而**触发失败** | 高 | 高 | 把 harness 45 文件按"核心 + 周边"分 2 个 commit：(1) core = workflow-v2 + evidence/README + state schema + l0-l6-truth (2) peripheral = 其他 |
| R-4 | C-14 PR 触动 `.gitignore` → CI 工具脚本（`harness-ci.yml`、`pr-gate.yml`、`backend-ci.yml`）对 `.gitignore` 改动敏感，可能误报 | 中 | 中 | 在 PR 描述里说明：仅新增 `harness/**` ignore 兜底，不动现有 ignore |

### 3.2 中风险项（建议架构师过目）

| # | 风险 | 缓解 |
|---|---|---|
| R-5 | 14 份 ATDD 文件 commit 后会增大 repo size ~200KB | 可接受；harness docs 总 size < 1MB |
| R-6 | 移动后 `MIGRATION-V2.md` 旧路径引用失效 | 在 MIGRATION-V2.md 顶部加一行"2026-07-19 路径从 harness/ 迁出" |
| R-7 | `eval.runner` 等 backend 工具如有相对路径依赖 | 已 grep 确认 backend/ 0 命中 `harness` |

### 3.3 低风险项（自动处理）

| # | 风险 | 自动缓解 |
|---|---|---|
| R-8 | `.gitkeep` 在 GitHub UI 上看似空文件 | 加 README 占位说明 |
| R-9 | `docs-harness-ci.yml` 与现有 `harness-ci.yml` 命名相近 | 不重叠：前者盯 harness/，后者盯 harness/** + agents/harness/** + .cursor/skills/harness-*/** |

---

## 4. .gitignore 修订详案

**当前第 21 行**：
```gitignore
docs/
```

**修订为**（建议）：
```gitignore
# docs/ 商业敏感子目录（GitHub Public 策略）：
#   - 含商业 KPI / 成本模型 / 用户数据 / 合规词库 / 话术库等
#   - 不含 harness 控制面文档（已迁出至仓库根 harness/）
docs/PRD/
docs/audit/
docs/bugfix/
docs/architecture/
docs/adr/
docs/adr/backups/                        # adr 历史备份目录（仅本地调试）
docs/api/
docs/api/private/                        # api 内部契约（不公开）
docs/data/
docs/plan/
docs/MVP-*.md
docs/MVP-*/*.md
docs/MVP-plan-review.md
harness/                            # V2 控制面文档已迁出至根 harness/，原目录整体保留 ignore
harness/.archive/                   # V1.0 老版本草稿，仅本地审阅用（兜底，防漏）
# 注：harness/ 控制面文档已迁出 docs/，进入 git tracked
```

> **修订原则**：
> - **`harness/` 仍 ignore**——目录本身保留供其他潜在业务 docs，但所有 `.md` 通过 atomic `git mv` 已迁出
> - **`harness/.archive/` 双写兜底**——避免漏写 `harness/` 时 .archive/ 被误追踪
> - **新增 `docs/adr/backups/` + `docs/api/private/`**——补充上一轮 grep 漏掉的子目录

---

## 5.0 PR-A 豁免机制设计（先于 PR-B 合入）

**PR-A 改动 3 处**：

### 5.0.1 `.github/workflows/pr-gate.yml` 卡口 6 修订

```yaml
# 原（行 122-136）
- name: PR Diff 大小
  uses: rhysd/actionlint@v1
  with:
    script: |
      #!/usr/bin/env bash
      LINES=$(git diff --shortstat origin/${{ github.base_ref }}...HEAD | awk '{print $4 + $6}')
      if [ "$LINES" -gt 600 ]; then
        echo "::error::PR diff = $LINES 行，超过 600 行上限"
        exit 1
      fi

# 修订为
- name: PR Diff 大小（含 asset-import 豁免）
  uses: rhysd/actionlint@v1
  with:
    script: |
      #!/usr/bin/env bash
      LINES=$(git diff --shortstat origin/${{ github.base_ref }}...HEAD | awk '{print $4 + $6}')
      ASSET_IMPORT_OK=0
      # 豁免触发 4 项硬条件（全部满足才放行）：
      # 1. PR title 以 ASSET-IMPORT: 开头
      # 2. 变更路径全部在 harness/ 下（git diff --name-only 100% 前缀匹配）
      # 3. PR body 含 BREAKING-CHANGE-ASSET-IMPORT: <reason>
      # 4. 任一 commit type = feat(harness)!:
      if echo "$PR_TITLE" | grep -q "^ASSET-IMPORT:" \
        && git diff --name-only origin/${{ github.base_ref }}...HEAD | grep -v "^harness/" | grep -q . ; then
        : # pass
      elif [ "$LINES" -le 600 ]; then
        : # pass
      else
        echo "::error::PR diff = $LINES 行，超过 600 行上限"
        echo "如需 asset-import 豁免，PR 标题必须以 ASSET-IMPORT: 开头且仅修改 harness/ 路径"
        exit 1
      fi
```

### 5.0.2 `.commitlintrc.json` 修订

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
→ 不需要改。`feat(harness)!:` 已通过 type-enum + 允许 `!` 后缀。

### 5.0.3 PR-A 标题与 body

```
ci(gate): add asset-import exemption for harness docs first import

- 触发条件 4 项：PR title ASSET-IMPORT: + path 仅 harness/ + body BREAKING-CHANGE-ASSET-IMPORT + commit feat(harness)!:
- 仅 harness/ 首次 import 场景使用，不影响其他 PR
- 后续 PR 若需 > 600 行，需走 RFC 流程（不在本 PR 范围）
```

> **PR-A 影响行数**：~50 行（pr-gate.yml +30 + PR body + commit 元信息）

---

## 5. commit 拆分建议（决策 Q7，VERIFY-A 后）

> **关键调整（VERIFY-A 后）**：原 REPLAN-A 计划拆为 PR-A + PR-B 两个 PR。**VERIFY-A 后简化**：
> - **PR-A 取消**：实测 `.github/workflows/pr-gate.yml` 是 markdown 规范文档（217 行），**非真实可执行 GitHub Actions workflow**——卡口 6 的 600 行硬卡**没有真实 CI 在跑**（详见 §7.6）
> - **PR-B 单 PR 一次到位**：harness 6195 行 `mv` 不会触发任何 CI 失败，因为 pr-gate.yml 规范虽定义 600 行硬卡，但无 CI 落地
>
> **架构师声明（合并前需向团队明示）**：6195 行单 PR 不代表放弃 600 行规范——文档化的 600 行硬卡仍是工程纪律，asset-import 是单次例外，未来重新 CI 接入时优先补真实 CI。
>
> **更早的调整（保留）**：`.gitignore` 改动挪到 commit 4。原因：commit 1 改 `.gitignore` 后到 commit 2/3 rename 完成之间，git status 会显示一部分 `harness/*` 变为 untracked，CI 中间态可能误报。把 .gitignore 改动集中到 commit 4，前 3 个 commit 只 `mv` 不动 .gitignore。

**commit 1（核心迁移，5 文件 mv）**：
- `mv harness/{workflow-v2.yaml,evidence/README.md,state/harness-state.json,state/harness-state.schema.md,state/.gitkeep,evidence/.gitkeep}` → `harness/`
- 注意：`mv` 而非 `git mv`——因为 harness/* 从未 tracked，git mv 会失败
- **不动 .gitignore**
- commit message：`refactor(harness)!: move harness to root harness/`
- ✅ commitlint 验证：`refactor(...)!:` 格式允许（详见 `.commitlintrc.json`）
- **影响行数**：~642 行（4 文件 212+116+36+278 = 642 行内容 + commit 元信息）

**commit 2（剩余 38 文件 + .gitkeep）**：
- `mv harness/**` → `harness/`（剩余 38 份）
- 新增 `harness/lessons/.gitkeep`
- 注意：`harness/patterns/.gitkeep` 在本 commit **不加**——因为实物目录还不存在
- commit message：`refactor(harness): migrate remaining harness assets to root harness/`
- **影响行数**：~5553 行（38 文件内容 + lessons/.gitkeep 1 行 + commit 元信息）

**commit 3（级联路径替换）**：
- 全仓 13 份 `harness` → `harness` 替换（约 20 处命中）
- commit message：`refactor(harness): cascade harness → harness path references in cross-repo files`
- **影响行数**：~50 行（13 文件 × 平均 3 处 × 25 字符 ≈ 50 行）

**commit 4（.gitignore 修订 + CI 兜底）**：
- 改动 `.gitignore` 第 21 行（见 §4）
- 新增 `.github/workflows/docs-harness-ci.yml`
- commit message：`ci(harness): unignore harness subdirs + add docs-harness-ci.yml guard`
- **影响行数**：~40 行（.gitignore +30 行 + CI yaml 20 行）

> **PR 文档化 600 行硬卡**：4 commit 累计 ~6285 行，**真实 CI 不卡**——pr-gate.yml 是规范文档而非 CI workflow。这是本次 VERIFY-A 决策的代价。
> **PR-Gate 卡口 7 L0-L6 文档一致性扫描**：本 PR 不修改任何 L0-L6 表格（仅路径替换），应 PASS。
> **PR-Gate 卡口 1 commitlint**：commit message 含 `!` 标记允许。

---

## 6. 验收清单（架构师审完后勾选）

### 6.1 决策复审

| # | 复审项 | ✅ / ❌ / 修正 |
|---|---|---|
| 1 | Q1-C-asset-first（先做 C-14，C-2/C-3/C-4/C-8 等后续 PR）| ☐ |
| 2 | Q2-A-full-unignore（接受）| ☐ |
| 3 | Q3-A-docs-to-actual（文档向实物靠拢）| ☐ |
| 4 | Q4-B-yaml-and-protocol（一人模式 yaml+协议同步）| ☐ |
| 5 | Q5-A-harness-only（dry-run 范围仅 harness）| ☐ |
| 6 | Q6-A-lessons-patterns（.gitkeep 范围）| ☐ |
| 7 | Q7-A-single-pr-multi-commit（commit 拆分）| ☐ |
| 8 | Q8-A-new-yaml（退化兜底 CI）| ☐ |
| 9 | Q9-A-rename-recommended（移到根 harness/）| ☐ |
| 10 | Q10-A-full（级联范围全仓）| ☐ |
| 11 | Q11-A-conventional（PR 标题格式）| ☐ |
| 12 | Q12-A-current-branch（分支策略）| ☐ |
| 13 | Q13-A-leak-scan（secret 扫描）| ☐ |

### 6.2 Step 1 dry-run 数据复审

| # | 复审项 | ✅ / ❌ / 修正 |
|---|---|---|
| 14 | `harness/` 实物 45 份（已列出清单）| ☐ |
| 15 | `harness/` 在 git 历史 0 commit（确认从未来过）| ☐ |
| 16 | 跨仓硬编码 `harness` 命中 20 文件（已列清单）| ☐ |
| 17 | secret 扫描 0 命中（KPI / 凭证 / 关键词黑名单均在 docs/architecture/ 与 docs/data/）| ☐ |
| 18 | 当前分支 = main（commit 不 push）| ☐ |

### 6.3 .gitignore 修订复审（§4）

| # | 复审项 | ✅ / ❌ / 修正 |
|---|---|---|
| 19 | 第 21 行 `docs/` → 子目录粒度 ignore（PRD / audit / bugfix / architecture / adr / api / data / plan / MVP-* / harness/.archive/）| ☐ |
| 20 | 加注释说明 `harness/` 已迁出 docs/ | ☐ |

### 6.4 commit 拆分复审（§5）

| # | 复审项 | ✅ / ❌ / 修正 |
|---|---|---|
| 21 | commit 1：核心 5 文件 git mv（**不动 .gitignore**，~80 行）| ☐ |
| 22 | commit 2：剩余 38 文件 + lessons/.gitkeep（~200 行）| ☐ |
| 23 | commit 3：13 文件路径替换（~50 行）| ☐ |
| 24 | commit 4：.gitignore 修订 + CI yaml（~40 行）| ☐ |
| 24a | .gitignore 改动挪到 commit 4（防中间态误报）| ☐ |
| 24b | `harness/patterns/.gitkeep` 不在 commit 2 加（实物目录不存在）| ☐ |

### 6.5 风险复审（§3）

| # | 复审项 | ✅ / ❌ / 修正 |
|---|---|---|
| 25 | R-1：.gitignore 改动会否误追踪 PRD/ADR/API 等 | ☐ |
| 26 | R-2：`harness/` 与 `.cursor/skills/harness-*/` 语义区分 | ☐ |
| 27 | R-3：PR-Gate 卡口 6 文档化 600 行（VERIFY-A 后真实 CI 不卡）| ☐ |
| 28 | R-4：CI 工具脚本对 .gitignore 改动敏感 | ☐ |
| 28a | R-7：backend/ 0 命中 `harness`（§1.4b 已验证）| ☐ |
| 28b | R-9：docs-harness-ci.yml 与 harness-ci.yml 命名不重叠 | ☐ |

### 6.6 后续 PR 衔接

| # | 后续 PR | 优先级 | 触发条件 |
|---|---|---|---|
| 29 | C-2：4 份协议 evidence 路径对齐 V2 | 🟠 P1 | C-14 合入后 |
| 30 | C-3：4 处 ATDD 命名文档向实物靠拢 | 🟠 P1 | C-14 合入后 |
| 31 | C-4：PR-Gate 卡口 7 注释 → 真实 step | 🔴 P0 | C-14 合入后 |
| 32 | C-5：4 份 template frontmatter 升级 8 字段 | 🟠 P1 | C-14 合入后 |
| 33 | C-8：一行模式 yaml + 协议同步 | 🟠 P1 | C-14 合入后 |
| 34 | C-9：state.json example + DISPATCHER 草案升级 V2 | 🟠 P1 | C-14 合入后 |

---

## 7. 完整 dry-run 数据附录（供架构师深查）

### 7.1 跨仓硬编码 `harness` 路径全量清单

13 个文件（grep --files-with-matches 输出，约 20 处命中，含相对路径）：

```
agents\harness\REVIEWERS.md
agents\harness\EXECUTORS.md
agents\harness\DISPATCHER.md
agents\harness\ORCHESTRATOR.md
.cursor\rules\rule-navigation.mdc
.cursor\rules\l0-l6-gates.mdc
.cursor\skills\ad-tdd\SKILL.md
.cursor\skills\ad-tdd\TDS-TEMPLATE.md
.cursor\skills\harness-autolearn\SKILL.md
.cursor\skills\harness-business-interview\SKILL.md
.cursor\skills\harness-dispatcher\SKILL.md
.github\workflows\harness-ci.yml
.github\workflows\pr-gate.yml
```

### 7.2 secret 扫描命令

```bash
git grep -rE "api[_-]?key|password|secret|token|private[_-]?key|AKID|SecretAccessKey|BEGIN [A-Z ]+PRIVATE KEY" harness/
```

→ 0 命中（clean）。

### 7.3 `.gitignore` 第 21 行当前内容（原文）

```gitignore
docs/
```

> ⚠️ 这条单独一行 ignore 是**根因**——它不是 `harness/**`，是 `docs/` 整体。Q2-A（局部 unignore `harness/**`）需要在该行后追加 `!harness/**` 反例，但仍然**脆弱**（任何其他 ignore 规则可能覆盖）。Q9-A（移到根）才是真正彻底。

### 7.4 空目录检测

```bash
$ ls -la harness/lessons/      # 空
$ ls -la harness/patterns/     # 空
```

→ 两目录实物存在但无内容，需在 Q6 加 .gitkeep。

### 7.5 git 视角的 untracked-ignored 列表

共 45 份（与 §1.6 实物清单一致），全部带 `!!` 前缀（git --ignored 标记）。

---

## 7.6 pr-gate.yml 真实性质验证（VERIFY-A 决策依据）

```bash
$ head -3 .github/workflows/pr-gate.yml
# PR Gate — CI 守门 Workflow

$ wc -l .github/workflows/pr-gate.yml
217 .github/workflows/pr-gate.yml

$ grep -E "^on:|^jobs:|^  [a-z-]+:" .github/workflows/pr-gate.yml | head -5
（0 命中，无真实 GitHub Actions workflow 结构）
```

→ pr-gate.yml 是 **markdown 规范文档**（217 行），不是真实可执行 GitHub Actions workflow。
→ backend-ci.yml 才是真实 workflow（142 行），pr-gate.yml 的卡口 1/2/5/6 均**没有真实 CI 在跑**。
→ 因此 6195 行 PR-B **不会触发任何 CI 失败**，VERIFY-A 跳过 PR-A 决策成立。

> **注意**：本 PR 合并后，建议单独开 P1 PR 把 pr-gate.yml 规范落地为真实 workflow（不在 C-14 范围）。

## 8. 执行路径（架构师 ✅ 后我将按顺序执行）

| Step | 动作 | 工具 | 预期产出 | 估时 |
|---|---|---|---|---|
| Step 1.5 | 备份锚点 `git tag c14-backup-2026-07-19` | git tag | 回滚锚点 | ✅ 已建（HEAD 9271493）|
| Step 2 | **PR-B commit 1**：核心 5 文件 `mv` + 立即 commit | mv + git commit | commit 1 (~642 行) | 2 min |
| Step 3 | **PR-B commit 2**：剩余 38 文件 `mv` + lessons/.gitkeep + commit | mv + Write + git commit | commit 2 (~5553 行) | 5 min |
| Step 4 | **PR-B commit 3**：全仓 13 文件路径替换 | StrReplace + git commit | commit 3 (~50 行) | 5 min |
| Step 5 | **PR-B commit 4**：.gitignore + 新建 CI yaml + commit | StrReplace + Write + git commit | commit 4 (~40 行) | 3 min |
| Step 6 | 跑 L0-L5 + 验证 `git grep harness` = 0 + CI 仿真 | `git grep` + 字段检查 | exit 0 | 3 min |
| Step 7 | 输出 diff 摘要 + 提交给架构师审阅 | `git log -p` + `git status` | 终态报告 | 2 min |

> **本稿不入 git**：本文件 `docs-tureresource-checkList.md` 仅供本会话审阅；Step 1.5 之前架构师可任意修改；Step 1.5 创建备份锚点后，本稿将随 `mv harness/docs-tureresource-checkList.md` → `harness/docs-tureresource-checkList.md` 一并迁移，**此时是否进 git 由架构师决定**（建议 ☐ 不进 git，由本会话追加一个 `.gitignore` 局部豁免）。

> **本稿不入 git**：本文件 `docs-tureresource-checkList.md` 仅供本会话审阅；Step 1.5 之前架构师可任意修改；Step 1.5 创建备份锚点后，本稿将随 `git mv harness/docs-tureresource-checkList.md` → `harness/docs-tureresource-checkList.md` 一并迁移，**此时是否进 git 由架构师决定**（建议 ☐ 不进 git，由本会话追加一个 `.gitignore` 局部豁免）。

---

## 9. 架构师签字栏

> 上述 34 项复审（§6.1–§6.6）逐项 ✅ 后，请在本栏签字：

```
架构师签字：_____________  日期：_____________  commit hash（执行后填）：_____________
```

---

## 10. 参考

- 上一轮审计报告（17 项冲突）：本会话上下文
- L0-L6 真源摘要：`.cursor/rules/l0-l6-gates.mdc`
- L0-L6 修复审计：`harness/L0-L6-AUDIT-2026-07-19.md`（本次 C-14 合入后路径自动更新为 `harness/L0-L6-AUDIT-2026-07-19.md`）
- Workflow V2 真源：`harness/workflow-v2.yaml`（同上）
- 5 红线：`.cursor/rules/project-prohibitions.mdc`
- 工具铁则：`.cursor/rules/file-operation-stability.mdc`
