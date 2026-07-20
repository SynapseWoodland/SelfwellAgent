---
name: harness-context-security-test
description: >
  SECURITY_TEST phase context template。V2 新增 phase。
  当 dispatcher 路由到 SECURITY_TEST 时由 security-reviewer 角色 Read。
disable-model-invocation: true
---

# SECURITY_TEST Phase Context

> **V2 新增 phase**。当 VERIFY 通过后进入 SECURITY_TEST，由 security-reviewer 执行独立安全评审。

## 一、必读

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `evidence/06-code.md` | CODE phase 产出，确认代码范围 |
| 2 | `evidence/07-verify.md` | VERIFY phase 结果，确认基础测试通过 |
| 3 | `.cursor/rules/coding-standards/RULES.md` | 安全规则部分 |
| 4 | `docs/architecture/adr/README.md` | 确认技术选型合规性 |

## 二、禁止

| 禁止行为 | 原因 |
|----------|------|
| 写代码 / 修改业务文件 | 越权；security-reviewer = 评审，非执行 |
| 读取 PRD / ARCH 原文 | 上下文隔离 |
| 跳到 DEPLOY | 必须 SECURITY_TEST 签字后才能进入 DEPLOY |

## 三、必产物

| 产物 | 文件路径 | 说明 |
|------|----------|------|
| 安全评审证据 | `evidence/08-security-test.md` | 8 字段 frontmatter + 三段式 |
| bandit 扫描结果 | 在 evidence 正文中记录命令和输出摘要 | 工具输出不上传，只记录关键指标 |

### 安全评审 Checklist

| 检查项 | 触发条件 | 操作 |
|--------|----------|------|
| SQL 注入 | 任何涉及 DB 操作的代码 | grep `sqlalchemy.*execute\|raw.*sql` |
| LLM prompt 注入 | 任何涉及 user input → LLM 的代码 | 检查 input sanitization |
| 敏感信息泄露 | 任何涉及密钥 / token / password 的代码 | grep `api_key\|secret\|password\|token` |
| 依赖漏洞 | 任何新增依赖 | `pip audit` / `safety check` |
| 权限越界 | 任何涉及 user role / permission 的代码 | 检查 RBAC 实现 |

## 四、退出条件

SECURITY_TEST 退出必须同时满足：

1. ✅ `evidence/08-security-test.md` 已写入，`signed: true`
2. ✅ bandit 扫描无 S/F 高危漏洞（允许 INFO/WARNING）
3. ✅ 无未处理的 PII 处理问题
4. ✅ `interrupt_budget` 已同步到 state.json

## 五、与其他 phase 的关系

```
VERIFY ──(通过)──> SECURITY_TEST ──(通过)──> DEPLOY
                              ↑
                     security-reviewer 签字
```

## 六、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`
- evidence schema：`harness/evidence/README.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
