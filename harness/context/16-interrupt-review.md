---
name: harness-context-interrupt-review
description: >
  INTERRUPT_REVIEW phase context template。V2 新增 phase。
  当 dispatcher 路由到 INTERRUPT_REVIEW 时由 quality-guardian 角色 Read。
disable-model-invocation: true
---

# INTERRUPT_REVIEW Phase Context

> **V2 新增 phase**。任一可打断 phase（`interruptible: true`）收到用户追问时进入 INTERRUPT_REVIEW。
> 由 quality-guardian 执行追问日志审查 + 继续/推迟决策。

## 一、必读

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `harness-state.json` | 当前状态，确认 `interrupted_phase` 和 `interrupt_budget` |
| 2 | `evidence/<interrupted_phase>.md` | 被中断 phase 的 evidence，确认当时状态 |
| 3 | `harness/context/phase-checklist.md` | 被中断 phase 的 context checklist |
| 4 | `harness/evidence/README.md` | evidence schema，确认 8 字段 |

## 二、禁止

| 禁止行为 | 原因 |
|----------|------|
| 未经 budget 检查直接进入 | budget 耗尽需要 AskUser 授权 |
| 修改被中断 phase 的 evidence | 保持 evidence 不可变性 |
| 直接跳过被中断 phase | 必须经过 INTERRUPT_REVIEW 决策 |

## 三、必产物

| 产物 | 文件路径 | 说明 |
|------|----------|------|
| 中断审查证据 | `evidence/16-interrupt-review.md` | 8 字段 frontmatter + 三段式 |
| 追问日志 | 在 evidence 正文中记录追问内容摘要 | 1-3 句 |
| 决策 | 在 evidence 正文中记录继续 / 推迟 / 升级 | 需说明理由 |

### INTERRUPT_REVIEW Checklist

| 检查项 | 操作 |
|--------|------|
| budget 检查 | 读取 `interrupt_budget`，若 ≤0 → AskUser 授权 |
| 追问日志审查 | 记录追问内容，确认追问意图 |
| 决策：继续（Continue） | 追问不改变 phase 走向，恢复 `$interrupted_phase` |
| 决策：推迟（Defer） | 追问揭示重大风险，标记为 `deferred_risks`，返回 PRD |
| 决策：升级（Escalate） | 追问揭示 blocker，触发 AskUser 决策 |
| budget 扣减 | 决策后 `interrupt_budget - 1`，同步到 state.json |

## 四、决策类型

### Continue（继续）

适用场景：追问澄清了实现细节，不影响 phase 走向。

操作：恢复 `$interrupted_phase`，继续执行。

### Defer（推迟）

适用场景：追问揭示了技术债务 / 设计缺陷，需要在新一轮 PRD 中处理。

操作：记录 `deferred_risks`，返回 `DATA_REPLAY`，随后开始新一轮 `PRD`。

### Escalate（升级）

适用场景：追问揭示了 blocker（如业务方向变更、资源限制、合规问题）。

操作：记录 `escalation_reason`，触发 AskUser 请求人工决策。

## 五、退出条件

INTERRUPT_REVIEW 退出必须同时满足：

1. ✅ `evidence/16-interrupt-review.md` 已写入，`signed: true`
2. ✅ 决策已明确（Continue / Defer / Escalate）
3. ✅ `interrupt_budget` 已扣减并同步到 state.json
4. ✅ 决策操作已执行（恢复 / 推迟 / 升级）

## 六、与其他 phase 的关系

```
任一 interruptible phase ──(追问)──> INTERRUPT_REVIEW ──(决策)──> 恢复 / 推迟 / 升级
                                               ↑
                                    quality-guardian 签字
```

## 七、interrupt_budget 消耗规则

| 操作 | budget 变化 | 备注 |
|------|-------------|------|
| 进入 INTERRUPT_REVIEW | -1 | 每次追问消耗 1 次 |
| AskUser 授权后继续 | 重置为 5 | budget 超限后用户授权可重置 |
| 新 run 开始 | 重置为 5 | 每次新的 feature run 从 5 开始 |

## 八、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`
- evidence schema：`harness/evidence/README.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
