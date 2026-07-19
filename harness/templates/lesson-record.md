---
name: harness-template-lesson
description: >
  lesson 三段模板（根因 / 修复 / 触发条件）。
  Phase 8-10 跑出真实问题后由任一角色填写，沉淀到 harness/lessons/。
disable-model-invocation: true
---

# Lesson 模板（含晋升机制）

> **使用方式**：复制本文件到 `harness/lessons/<YYYY-MM-DD>-<slug>.md`，保留 frontmatter，正文按三段填空。

## §〇 晋升机制（lesson → pattern → instinct）

| 级别 | 触发条件 | 沉淀位置 | 评估方 |
|------|---------|---------|--------|
| **lesson** | 单次真实问题 | `harness/lessons/` | 触发角色 |
| **pattern** | lesson 出现 ≥ 2 次同类问题（90 天内 / 不同 FR） | `coding-standards/PATTERNS.md` 反模式速查表 | harness-autolearn |
| **instinct** | pattern 实战 ≥ 3 次 + 人工确认 | `coding-standards/RULES.md` | orchestrator + 人工 |

**铁律**：每次写 lesson 必须**同时**填 §3 触发条件 + §4 是否晋升评估，不能跳过。

## Frontmatter（强制）

```yaml
---
lesson_id: LSN-<YYYY-MM-DD>-<seq>
created_at: <ISO 8601>
fr_id: <FR-XXX-XX 或 NONE>
phase: <触发 phase，如 VERIFY>
trigger_agent: <触发本次踩坑的角色>
severity: blocker / major / minor
schema_version: "1.0"
---
```

## 1. 根因

> 一句话描述**为什么会发生**，而非"发生了什么"。

- **直接触发**：...
- **深层原因**：...
- **遗漏环节**：...

## 2. 修复

> 一句话描述**怎么修的**。

- **改动文件**：`backend/...` / `apps/...` / `docs/...`
- **改动类型**：code / test / doc / config / process
- **回滚成本**：低 / 中 / 高
- **是否已合并**：是 / 否

## 3. 触发条件

> **本类问题将来如何被自动检测**。这是 lesson 能否晋升为 pattern / instinct 的关键。

- **可观测信号**：日志关键词 / 监控指标 / 测试断言 / CI 失败模式
- **检测工具**：pytest / ruff / mypy / bandit / Golden Set / pr-gate / 自定义脚本
- **检测位置**：本地 pre-commit / CI / 监控告警 / 人工 review
- **检测成本**：低 / 中 / 高

## 4. 是否晋升（harness-autolearn 自动评估）

- [ ] 触发条件可机器检测
- [ ] 同类问题在过去 90 天内出现 ≥ 2 次（不同 FR）
- [ ] 修复方式可抽象为通用 pattern

> 若以上 3 项全勾选 → 写 `harness/lessons/<date>-<slug>-PATTERN.md` 并加入 coding-standards/PATTERNS.md 反模式速查表。

## 5. 决策请求

- [ ] 是否在本次 PR 中同步修复？
- [ ] 是否立刻晋升为 pattern？
- [ ] 是否需要追加 acceptance 场景？

## 参考

- 状态机：`harness/workflow.yaml`
- 晋升机制：见本文件 §〇（自包含）
- 现有反模式表：`.cursor/skills/coding-standards/PATTERNS.md`
