---
name: harness-context-ops-loop
description: >
  OPS_LOOP phase context template。V2 新增 phase。
  当 dispatcher 路由到 OPS_LOOP 时由 tester 角色 Read。
disable-model-invocation: true
---

# OPS_LOOP Phase Context

> **V2 新增 phase**。INCIDENT_RESPONSE 完成后进入 OPS_LOOP，由 tester 执行灰度策略和 A/B 实验验证。

## 一、必读

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `evidence/13-incident-response.md` | INCIDENT_RESPONSE phase 产出，确认修复措施 |
| 2 | `evidence/11-signoff.md` | SIGN_OFF phase 产出，确认基线版本 |
| 3 | `docs/PRD/*` | 原始 PRD，确认业务指标 |
| 4 | `docs/api/error-codes-spec.md` | 错误码规范 |

## 二、禁止

| 禁止行为 | 原因 |
|----------|------|
| 跳过灰度直接全量发布 | OPS_LOOP 的核心目的就是控制风险 |
| 修改 A/B 分组规则 | 破坏实验有效性 |
| 在数据不足时做决策 | 统计显著性要求 |

## 三、必产物

| 产物 | 文件路径 | 说明 |
|------|----------|------|
| 灰度验证证据 | `evidence/14-ops-loop.md` | 8 字段 frontmatter + 三段式 |
| 灰度报告 | 在 evidence 正文中记录灰度比例 / 流量 / 指标变化 | 需量化 |
| A/B 实验结果 | 在 evidence 正文中记录实验组 vs 对照组指标对比 | 需统计显著性 |

### OPS_LOOP Checklist

| 检查项 | 操作 |
|--------|------|
| 灰度策略验证 | 确认灰度比例逐步提升（5% → 20% → 50% → 100%） |
| 核心指标监控 | LLM 成本 / 延迟 SLO / 错误率在灰度期间无退化 |
| A/B 实验设计 | 确认实验组和对照组流量分配合理 |
| 数据充分性 | 确认实验运行时间足够（至少 24 小时或达到统计显著性） |
| 决策 | 灰度成功 → 继续；灰度失败 → 触发 INCIDENT_RESPONSE（新一轮） |

## 四、退出条件

OPS_LOOP 退出必须同时满足：

1. ✅ `evidence/14-ops-loop.md` 已写入，`signed: true`
2. ✅ 灰度策略已验证（全量或回退决策明确）
3. ✅ A/B 实验结果已记录（无论成功或失败）
4. ✅ 核心指标无退化
5. ✅ `next_phase_hint` = `"SKILL_UPDATE"` 已写入 state.json

## 五、与其他 phase 的关系

```
INCIDENT_RESPONSE ──(冷静期后)──> OPS_LOOP ──(验证通过)──> SKILL_UPDATE
                                         ↑
                                    tester 签字
                                         ↓
                              灰度成功 ──> DEPLOY（全量）
                              灰度失败 ──> INCIDENT_RESPONSE（新一轮）
```

## 六、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`
- evidence schema：`harness/evidence/README.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
