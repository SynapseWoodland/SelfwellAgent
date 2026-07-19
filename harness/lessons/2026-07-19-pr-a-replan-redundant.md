---
date: 2026-07-19
fr_refs: [C-14-HARNESS-IMPORT]
root_cause: 凭"6195 行 vs PR-Gate 600 行硬卡"的数字直觉触发 REPLAN-A，但未先验证 pr-gate.yml 是不是真 CI，导致额外一轮 checklist 修订（§5.0/§6.7/§3.3/§6.5 共 4 处）+ 多走 2 轮 AskUser 决策
confirmed_count: 1
status: active
---

## 触发场景

2026-07-19 C-14 路径迁移。当实测 `harness/` 总行数 6195 行 + 单文件最大 463 行（ATDD-M5-AC.md）时，发现"无论如何拆都至少 1 个 PR 超 600 行硬卡"——立刻触发 REPLAN-A：拆 PR-A 加 asset-import 豁免机制 + PR-B 主迁移。checklist 增 §5.0（PR-A 设计 70 行）/§6.7（PR-A 复审 4 项）/§3.3 R-10（豁免滥用风险）/§6.5 #28c 共 4 处。架构师逐项复审通过后**起手 Step 3**，第一步就发现 pr-gate.yml 是 markdown 文档不是真 CI，整套 PR-A 设计作废。然后再次走 REPLAN-A → VERIFY-A 决策，把 §5.0 / §6.7 / R-10 / #28c 全部删除，又是一轮 checklist 修订。

**总代价**：
- checklist 修订 2 轮（加 PR-A + 删 PR-A）= 140 行无效改动
- AskUser 决策 4 轮（REPLAN-A / PR-LIMIT / NEXT-FINAL / ARCHITECT-DECISION / PR-A-VERIFY / VERIFY-A）
- 用户全程精力被消耗在"PR-A 是否真的需要"的来回上

## 根因分析

**直接触发**：PR-Gate 卡口 6 ≤ 600 行硬卡是文档化约束（实非真 CI）→ 数字直觉"6195 > 600 必须拆 PR" → 触发 REPLAN-A

**深层病根**：在 §1 dry-run 阶段没有把"pr-gate.yml 是否真 CI"作为 dry-run 必查项。checklist §1.1-§1.7 跑了 7 个事实段：
- §1.1 `git check-ignore` 实测
- §1.2 `git ls-files harness/`
- §1.3 `git log -- harness/`
- §1.4 全仓 grep 命中
- §1.5 secret 扫描
- §1.6 实物清单
- §1.7 当前分支 + commits

**漏掉了 §1.8 workflow 性质验证**——也就是 pr-gate.yml 是否真 CI 的检查。导致 REPLAN-A 阶段才发现，整套方案作废。

**为什么漏掉**：项目历史里 pr-gate.yml 一直是 markdown 文档，已被团队默认接受。**新人不读历史，误把文件名后缀当功能**。这种情况只有**实际跑一下 CI** 才能发现——但 REPLAN-A 阶段没人跑（也没必要跑，因为是新需求）。

**类似的反直觉案例**：
- 看到 `.gitignore` 里有 `docs/` → 推测"docs/ 整体 ignore" → 实际跑 `git check-ignore` 才确认（这个我们跑对了）
- 看到 pr-gate.yml 卡口 6 → 推测"CI 强制 600 行硬卡" → 实际跑 `head -3 .github/workflows/pr-gate.yml` 才能发现是 markdown

## 修复路径

### 1. 在 checklist §1 dry-run 加 §1.8

```
### 1.8 CI workflow 性质验证

```bash
$ for f in .github/workflows/*.yml; do
  first=$(head -1 "$f")
  jobs=$(grep -c "^jobs:" "$f" || echo 0)
  yaml_blocks=$(grep -c '```yaml' "$f" || echo 0)
  echo "$f: first=$first jobs=$jobs yaml_blocks=$yaml_blocks"
done
```

→ 若 `yaml_blocks > 0` 且 `jobs == 0`，**该文件是规范文档不是真 CI**
→ 这必须在 §REPLAN 阶段之前就完成
```

### 2. 决策前必跑"真伪验证 1 分钟测试"

| 想做什么 | 真伪测试 | 1 行命令 |
|------|------|------|
| 改 workflow 加新守门 | workflow 是真 CI 吗 | `head -1 file.yml && grep -c '^jobs:' file.yml` |
| 改 .gitignore 引入新路径 | 真 ignore 吗 | `git check-ignore -v path/to/file` |
| 改文档真源 | 是真源吗 | `git grep "<symbol>" -- '*.md' \| head` |
| 跑 PR 走守门 | 真守门吗 | `git log --oneline <file> -- .github/workflows/` |

**强约束**：任何**基于"前提条件 X 成立"的设计**，必须先 1 分钟验证 X 真伪。这是 checklist §1 dry-run 的核心目的。

### 3. 降低 REPLAN 反复的代价

| 反模式 | 正确做法 |
|------|------|
| 先 REPLAN-A，再发现作废，再 REPLAN-B | **先跑 §1.8 性质验证，再决定要不要 REPLAN** |
| AskUser 4 轮反复 | 把 dry-run §1 一次跑全，避免每发现一个新坑就 REPLAN |
| checklist 增改 → 删改（来回 2 轮）| 在 §1 dry-run 阶段**穷尽**前置依赖 |

### 4. 本次会话的实际修复（已做）

- ✅ VERIFY-A 后修订 §5 / §6.7 / §3.3 / §6.5 全部删除 PR-A 相关内容
- ✅ 加 §7.6 真实 workflow 验证节段
- ✅ 加 §7.1.8 决策前必跑"真伪验证"
- ✅ 实际运行：commit 1 (`d339e52`) + commit 2 (`a9a63db`) 一次性过，无 CI 卡口（与预期一致）

## 触发条件清单（grep 兜底）

```bash
# 1. 揪出"文档化 workflow"——见 c14-pr-gate-is-markdown.md §触发条件

# 2. 揪出"前后矛盾的设计决策"——同一份 checklist 出现 ≥2 次 "REPLAN-A" / "REPLAN-B"
for f in harness/checklist.md harness/checklist.md; do
  if [ -f "$f" ]; then
    replan_count=$(grep -c "REPLAN-" "$f")
    if [ "$replan_count" -gt 1 ]; then
      echo "MULTI-REPLAN CHECKLIST: $f ($replan_count replans)"
    fi
  fi
done

# 3. 揪出"4 轮以上 AskUser 决策"——同一次会话 chat history 反映
# 暂无自动 grep，但应人工 review 会话成本

# 4. 揪出"checklist 来回改"——git log 看 commit message 含 "修订" 字样的频率
git log --oneline --grep="修订" -10
```

## 相关 lesson

- `2026-07-19-powershell-utf8-chinese-corruption.md`：PowerShell 5.x Set-Content 默认 GBK 写文件导致中文乱码
- `2026-07-19-c14-pr-gate-is-markdown.md`：pr-gate.yml 是 markdown 文档不是真 CI workflow
