---
date: 2026-07-19
fr_refs: [C-14-HARNESS-IMPORT]
root_cause: 凭直觉假设 `.github/workflows/pr-gate.yml` 是真实 GitHub Actions workflow（含 `on:` / `jobs:` / `- name:` 可执行结构），导致基于此设计的 PR-A 加 asset-import 豁免机制整套方案无效
confirmed_count: 1
status: active
---

## 触发场景

2026-07-19 C-14 路径迁移 REPLAN 阶段。原计划是 1 PR + 4 commit，实测 `harness/` 总行数 6195 行，发现 PR-Gate 卡口 6（≤ 600 行硬卡）会爆；为绕开这个硬卡设计了 REPLAN-A：拆 PR-A 加 asset-import 豁免机制 + PR-B 主迁移。checklist 增 §5.0/§6.7/§3.3 R-10/§6.5 #28c 共 4 处修订，架构师复审 40 项后起手 Step 3——此时才发现 `.github/workflows/pr-gate.yml` **不是真实 GitHub Actions workflow**，而是 217 行 markdown 规范文档（含大量 ` ```yaml ` 代码块示例），**没有任何真实 CI 在跑 PR diff 行数硬卡**。整套 PR-A 设计前提不存在。

## 根因分析

**核心误判**：文件名后缀 `.yml` 在 GitHub 约定里就是 workflow，但本项目 `pr-gate.yml` 实际是**纯 markdown 文档**，内容形如：

```markdown
### 卡口 6：PR Diff 大小

```yaml
- name: PR Diff 大小
  uses: rhysd/actionlint@v1
  ...
```
```

代码块内的 yaml **永远不会被 GitHub Actions 执行**——只是给人看的规范示例。

**为什么没早发现**：
1. 文件 `.yml` 后缀符合 workflow 约定 → 名字暗示"可执行"
2. 文件内容**混排** markdown + yaml 块，没有清晰分界
3. 文档化"卡口 6 ≤ 600 行硬卡"是**业务纪律**，让人误以为是 CI 在强制执行
4. 项目还有 `backend-ci.yml`（真 workflow，142 行），混在一起增加判断难度

**对比真实 workflow 的特征**：

| 真 workflow | 本项目 pr-gate.yml |
|------|------|
| 文件首行 `name: ...` | 首行 `# PR Gate — CI 守门 Workflow`（注释） |
| 顶层 `on: / jobs:` | 顶层 `## 一、触发条件`（markdown 标题） |
| YAML 缩进结构严格 | markdown 段落 + ```yaml 块混排 |
| `git show .github/workflows/pr-gate.yml` 输出 yaml 解析 | 输出 markdown 文本 |

## 修复路径

### 1. 修订 checklist 与决策

按 VERIFY-A 决策：
- §5.0 PR-A 整段删除（asset-import 豁免机制不需要）
- §6.7 PR-A 复审 4 项删除
- §3.3 R-10 风险删除
- §6.5 #28c 复审项删除
- §8 执行路径从"PR-A → PR-B 串行"改为"PR-B 单 PR 一次到位"
- §5 commit 行数估算更新（commit 1 实际 708 行，commit 2 实际 8409 行）

### 2. 修订 GitHub workflow 设计哲学

`pr-gate.yml` 未来要么：
- **A. 改造为真 workflow**（去掉 markdown，把 7 卡口写成真 jobs），但需要补 L0-L4 后端环境（`uv` / `pytest` / `gh` 等）和 secrets
- **B. 改名 `pr-gate.md`**（明确是规范文档），后续单独建 `pr-gate-ci.yml` 真 workflow
- **C. 维持现状**（仅规范文档），由 pre-commit hook + 团队 review 兜底

本次会话决定 C（保持现状），理由是项目当前**只 backend-ci.yml 跑 L0-L4**，pr-gate 守门尚未真正 CI 化。

### 3. 沉淀教训

> **"规范文档" vs "真实 CI" 是两个完全不同的工程对象**——前者依赖团队纪律，后者由 GitHub Actions 强制。
> 设计新 PR 拆分策略前，必须**先验证守门机制是真的 CI 还是文档**。

## 触发条件清单（grep 兜底）

```bash
# 1. 揪出"文档化 workflow"——文件首行是 # 注释而不是 name: 的 workflow
for f in .github/workflows/*.yml; do
  first_line=$(head -1 "$f")
  if echo "$first_line" | grep -q "^#"; then
    echo "POTENTIAL DOC-WORKFLOW: $f"
  fi
done

# 2. 揪出"无 jobs: 顶层字段"——这意味着不是真 workflow
for f in .github/workflows/*.yml; do
  if ! grep -q "^jobs:" "$f"; then
    echo "NO-JOBS-WORKFLOW: $f"
  fi
done

# 3. 揪出 workflow 文件夹里的 markdown 痕迹（含 ```yaml 块）
for f in .github/workflows/*.yml; do
  yaml_block_count=$(grep -c '```yaml' "$f")
  if [ "$yaml_block_count" -gt 0 ]; then
    echo "MARKDOWN-WITH-YAML-BLOCKS: $f ($yaml_block_count blocks)"
  fi
done
```

> **强约束**：任何带 `MARKDOWN-WITH-YAML-BLOCKS` 标记的 workflow 文件，**在改 CI 守门策略前必须先 §VERIFY-A 检查**——验证是真 workflow 还是文档。

## 相关 lesson

- `2026-07-19-powershell-utf8-chinese-corruption.md`：PowerShell 5.x Set-Content 默认 GBK 写文件导致中文乱码
- `2026-07-19-pr-a-replan-redundant.md`：REPLAN-A 拆 PR-A 加豁免但前提不成立导致 checklist 浪费一轮
