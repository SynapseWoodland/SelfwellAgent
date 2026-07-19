---
name: harness-context-incident-response
description: >
  INCIDENT_RESPONSE phase context template。V2 新增 phase。
  当 dispatcher 路由到 INCIDENT_RESPONSE 时由 deployer 角色 Read。
disable-model-invocation: true
---

# INCIDENT_RESPONSE Phase Context

> **V2 新增 phase**。SIGN_OFF 完成后进入 INCIDENT_RESPONSE，由 deployer 执行故障响应流程。
> 触发时机：生产环境出现异常 / 监控告警 / 用户反馈重大问题。

## 一、必读

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `evidence/11-signoff.md` | SIGN_OFF phase 产出，确认最后稳定版本 |
| 2 | `evidence/09-deploy.md` | DEPLOY phase 产出，确认部署配置 |
| 3 | `docs/observability/dashboard.md` | 监控看板（若已落地） | W12 P2 3.2.4 前此项可跳过
| 4 | `docs/api/error-codes-spec.md` | 错误码规范，确认错误分类 |

## 二、禁止

| 禁止行为 | 原因 |
|----------|------|
| 在未分析根因前直接回滚 | 可能掩盖真正问题 |
| 在未通知 stakeholder 前对外发布 | 合规要求 |
| 跳过 INCIDENT_RESPONSE 直接进入 OPS_LOOP | 冷静期要求 |

## 三、必产物

| 产物 | 文件路径 | 说明 |
|------|----------|------|
| 故障响应证据 | `evidence/13-incident-response.md` | 8 字段 frontmatter + 三段式 |
| 故障报告 | 在 evidence 正文中记录故障时间线 / 根因 / 影响范围 | 影响范围需量化 |
| 修复计划 | 在 evidence 正文中记录短期 + 长期修复措施 | |

### INCIDENT_RESPONSE Checklist

| 检查项 | 操作 |
|--------|------|
| 故障确认 | 确认故障存在，记录发生时间、持续时间、影响范围 |
| 根因分析 | 5-Why 分析，记录根本原因 |
| 短期修复 | 立即可执行的缓解措施（如回滚、限流、熔断） |
| 长期修复 | 根本性解决方案，进入下一轮 PRD |
| 冷静期 | 响应完成后等待至少 1 小时，确认无复发 |
| stakeholder 通知 | 确认相关方已收到故障通知 |

## 四、退出条件

INCIDENT_RESPONSE 退出必须同时满足：

1. ✅ `evidence/13-incident-response.md` 已写入，`signed: true`
2. ✅ 根因分析已完成
3. ✅ 短期修复已部署并验证有效
4. ✅ 冷静期已过（无故障复发）
5. ✅ stakeholder 通知已发送
6. ✅ `next_phase_hint` = `"OPS_LOOP"` 已写入 state.json

## 五、与其他 phase 的关系

```
SIGN_OFF ──(通过)──> INCIDENT_RESPONSE ──(冷静期后)──> OPS_LOOP
                              ↑
                       deployer 签字
```

## 六、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`
- evidence schema：`harness/evidence/README.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
