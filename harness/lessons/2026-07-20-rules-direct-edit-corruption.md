---
date: 2026-07-20
fr_refs: [FR-ARCH-01]
root_cause: 直接编辑 alwaysApply .mdc 文件导致编码损坏，应通过 lesson 机制沉淀经验
confirmed_count: 1
status: active
---

# Lesson: 编辑 alwaysApply 规则文件必须遵循 Auto-Learn 机制

## 触发场景

修改 `.cursor/rules/` 下的 alwaysApply 文件（如 `ddd-bounded-context.mdc`、`coding-standards.mdc`、`project-meta.mdc`）时，直接使用 StrReplace 导致编码损坏，文件变成乱码。

## 根因分析

1. `.mdc` 文件是 Cursor 规则系统核心文件，有特殊 frontmatter 和编码要求
2. 直接编辑可能破坏文件的 UTF-8 编码结构
3. 违反了 harness-autolearn 的三级晋升机制：
   - 应该先写 **lesson** → `harness/lessons/`
   - 再由 orchestrator 决定是否晋升为 **pattern** 或 **instinct**

## 修复路径

1. 用 `git restore` 还原损坏的文件
2. 创建 lesson 文件记录本次经验
3. 后续规则变更遵循：
   - **lesson**：写入 `harness/lessons/`
   - **pattern**：晋升到 `.cursor/rules/python-patterns.mdc`
   - **instinct**：晋升到 `.cursor/rules/coding-standards.mdc`

## 触发条件清单

| 场景 | 正确做法 |
|------|---------|
| 修改 alwaysApply 规则 | 先创建 lesson，再通过晋升机制更新 |
| 多文件批量更新 | 按优先级逐个处理，避免编码漂移 |
| CI 检查失败 | 查看 lesson 文件，遵循 pattern/instinct 指引 |

## 参考

- 正确模式：`.cursor/skills/harness-autolearn/SKILL.md`
- 类似 lesson：`2026-07-19-powershell-utf8-chinese-corruption.md`
