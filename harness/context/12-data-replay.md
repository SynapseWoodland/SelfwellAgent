---
name: harness-context-data-replay
description: >
  DATA_REPLAY phase context template。V2 新增 phase。
  当 dispatcher 路由到 DATA_REPLAY 时由 requirement-analyst 角色 Read。
disable-model-invocation: true
---

# DATA_REPLAY Phase Context

> **V2 新增 phase**。SIGN_OFF 完成后进入 DATA_REPLAY，由 requirement-analyst 执行数据回流闭环验证。

## 一、必读

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `evidence/11-signoff.md` | SIGN_OFF phase 产出，确认最终交付物 |
| 2 | `docs/PRD/*` | 原始 PRD，确认业务目标 |
| 3 | `backend/app/db/models/harness_events.py` | 事件表 schema（若已落地） | W12 P2 3.2.2 前此项可跳过
| 4 | `docs/observability/dashboard.md` | 可观测看板（若已落地） | W12 P2 3.2.4 前此项可跳过

## 二、禁止

| 禁止行为 | 原因 |
|----------|------|
| 写代码 / 修改业务文件 | 越权；data replay = 评审，非执行 |
| 跳到 PRD | 必须 DATA_REPLAY 完成后再开始新一轮 |
| 忽略 PRD 偏差 | replay 的核心目的就是检测偏差 |

## 三、必产物

| 产物 | 文件路径 | 说明 |
|------|----------|------|
| 数据回流验证证据 | `evidence/12-data-replay.md` | 8 字段 frontmatter + 三段式 |
| replay session ID | 在 evidence 正文中记录新生成的 `replay_session_id` | UUID v4 格式 |

### DATA_REPLAY Checklist

| 检查项 | 操作 |
|--------|------|
| PRD 偏差检测 | 对比 SIGN_OFF 交付物 vs 原始 PRD，确认无偏离 |
| 指标闭环 | 确认核心指标（LLM 成本 / 延迟 SLO）有记录 |
| 教训提取 | 识别本轮教训，输出 1-3 条可复用的 pattern |
| replay_session_id 生成 | 生成新 UUID 记录在本轮 evidence 的 `replay_session_id` 字段 |

## 四、退出条件

DATA_REPLAY 退出必须同时满足：

1. ✅ `evidence/12-data-replay.md` 已写入，`signed: true`
2. ✅ PRD 偏差已记录（若有偏差）
3. ✅ 教训提取已完成
4. ✅ `replay_session_id` 已生成并同步到 state.json
5. ✅ `next_phase_hint` = `"auto-cycle-to-PRD"` 已写入 state.json

## 五、与其他 phase 的关系

```
SIGN_OFF ──(通过)──> DATA_REPLAY ──(完成)──> PRD（新一轮）
                                        ↑
                              requirement-analyst 签字
                                        ↓
                              replay_session_id 自增
```

## 六、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`
- evidence schema：`harness/evidence/README.md`
- harness-autolearn：`harness/lessons/`（教训沉淀位置）
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
