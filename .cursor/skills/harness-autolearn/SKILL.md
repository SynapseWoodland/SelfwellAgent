---
name: harness-autolearn
description: >
  Harness 记忆进化 skill。commit 后 / 用户说"/learn"/"沉淀经验"时触发；
  负责 lesson → pattern → instinct 三级晋升机制、判定阈值、文件路径 docs/harness/lessons/。
  本 skill 是 Harness 自我进化层，不修改任何业务文件。
  触发频率：每个 PR 合入后由 orchestrator 询问一次"是否沉淀"。
disable-model-invocation: false
---

# Harness Auto-Learn（A 档精简版）

> 记忆脊柱 = 踩坑 → lesson → pattern → instinct。避免"踩坑-忘坑-再踩"循环。

## 一、触发条件

| 触发 | 场景 |
|------|------|
| commit 后 | PR 合入 → orchestrator 询问"是否沉淀" |
| 显式 | "/learn" / "沉淀经验" / "升 pattern" / "升 instinct" |
| 跨多 run 比对 | 同类问题在 ≥ 2 个 FR 出现 → 触发晋升判定 |
| 实战冲突 | Pre-Mortem 发现新反模式 → 触发 lesson 速写 |

## 二、三级晋升机制

| 级别 | 文件落点 | 触发条件 |
|------|---------|---------|
| **lesson** | `docs/harness/lessons/<YYYY-MM-DD>-<slug>.md` | 1 次实战踩坑 |
| **pattern** | `.cursor/skills/coding-standards/PATTERNS.md` | 同类 lesson 在 ≥ 2 个不同 FR 出现 |
| **instinct** | `.cursor/skills/coding-standards/RULES.md` | pattern 实战 ≥ 3 run + 人工 confirm |

> **关键约束**：本 skill 只写 `docs/harness/lessons/`；pattern / instinct 写入由 orchestrator 在 SIGN_OFF 阶段主动合入（避免 auto-learn 改既有 Skill 漂移）。

## 三、晋升判定阈值

| 条件 | 阈值 |
|------|------|
| 1. lesson 立案 | 实战根因 ≥ 80 字即可 |
| 2. pattern 晋升 | 同类 lesson 在 ≥ 2 个不同 FR（`fr_refs` 取并集）出现 |
| 3. instinct 晋升 | pattern 验证 ≥ 3 run + 人工 `confirm: true` |
| 4. lesson 复发 | 同根因 90 天内再次出现 → 自动建议升 pattern |
| 5. instinct 撤回 | 实战违反 ≥ 2 次 → 降级回 pattern |

> **不写业务规则**：lesson / pattern 内容**不进入** `agents/` `rules/` 目录（R-2）。

## 四、lesson schema（5 字段 frontmatter，A 档精简）

```yaml
---
date: <YYYY-MM-DD>
fr_refs: [<FR-XXX-XX>, ...]
root_cause: <一句话根因>
confirmed_count: <int>          # 复发计数（≥2 触发 pattern 提示）
status: <active|resolved|expired>
---
```

正文 4 段：触发场景 / 根因分析 / 修复路径 / 触发条件清单（grep 兜底用）。完整模板见 `docs/harness/templates/lesson-record.md` §〇。

## 五、严格禁止（红线）

| # | 禁止 | 兜底 |
|---|------|------|
| 1 | 自动写 `coding-standards/PATTERNS.md` / `RULES.md` | 必须 orchestrator + 人工 |
| 2 | lesson 文件落点出 `docs/harness/lessons/` | pre-commit 路径 grep |
| 3 | 业务阈值硬编码入 lesson | grep `agents/` 扩展到 `lessons/`（R-2） |
| 4 | lesson 跨 FR 串联绕 pattern 判定 | 必填 `fr_refs` + 手动确认 |
| 5 | instinct 未经 ≥3 run 验证 + confirm 升级 | `confirmed_count` 校验 |

## 六、与其他 Skill 边界

| Skill | 关系 |
|-------|------|
| `coding-standards/SKILL.md` | **接力**——本 skill 不直接写 pattern，由 orchestrator SIGN_OFF 时写入 PATTERNS.md |
| `coding-standards/PATTERNS.md` | **被引用**——pattern 落地真源 |
| `coding-standards/RULES.md` | **被引用**——instinct 落地真源 |
| `pr-gate/SKILL.md` | **互斥**——pr-gate 不接受 auto-learn 路径下的修改 |

## 七、参考

- 模板：`docs/harness/templates/lesson-record.md`（含晋升机制 §〇）
- 协议：`agents/harness/ORCHESTRATOR.md`（SIGN_OFF 阶段主动询问）
- 状态机：`docs/harness/workflow.yaml`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2
