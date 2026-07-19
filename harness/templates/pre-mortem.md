---
name: harness-template-pre-mortem
description: >
  Pre-Mortem 模板。Phase 3（PRE_MORTEM）由 orchestrator 跨 5 评审角色调用。
  模板假设"上线 30 天后失败，列出 5 个根因"，输出缓解计划。
disable-model-invocation: true
---

# Pre-Mortem 模板

> **使用方式**：复制本文件到 `evidence/04-pre-mortem.md`，保留 frontmatter，正文按五段填空。

## Frontmatter（强制）

```yaml
---
evidence_id: EV-<YYYY-MM-DD>-<fr_id>-04
phase: PRE_MORTEM
role: orchestrator
author_agent: orchestrator
created_at: <ISO 8601>
fr_id: <FR-XXX-XX>
schema_version: "1.0"
---
```

## 1. 观点

> 假设本 FR **上线 30 天后被回滚**或**线上 P0 故障**。一句话总结最可能的失败类型。

（例：本功能因 Redis 连接池耗尽导致打卡接口大面积 5xx。）

## 2. 论据：5 个失败根因

> **必填 5 条**。每条 ≤ 3 行。来源标注：[requirement / tech / quality / security / devops]。

### 根因 1：[一句话标题]
- 来源：[requirement / tech / quality / security / devops]
- 描述：...
- 触发条件：...

### 根因 2：[一句话标题]
- 来源：...
- ...

### 根因 3：[一句话标题]
- 来源：...
- ...

### 根因 4：[一句话标题]
- 来源：...
- ...

### 根因 5：[一句话标题]
- 来源：...
- ...

## 3. 缓解计划

| 根因 | 缓解动作 | 负责 phase | 验收方式 |
|---|---|---|---|
| 1 | ... | Phase X | ... |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |
| 4 | ... | ... | ... |
| 5 | ... | ... | ... |

## §〇 Pre-Mortem 签字规则（A 档精简版）

| 类型 | 角色 |
|------|------|
| **必签 3 角色** | requirement-analyst、tech-architect、quality-guardian |
| **触发式扩展 2 角色** | security-reviewer（PII / LLM / 对外 API 时）、devops-reviewer（CI / 部署 / 迁移时） |

**触发式扩展规则**（任一命中即追加）：
- 涉及 PII / LLM 调用 / 对外 API / 密钥 → 必须追加 security-reviewer 签字
- 涉及 CI 配置 / 部署 / 数据库迁移 / 基础设施 → 必须追加 devops-reviewer 签字
- 未触发的角色 → 显式填"无意见 / 不适用"

## 3.5 对抗辩论附录（冲突时使用）

> **触发条件**：当 Pre-Mortem 中 5 评审对某根因或方案选择产生分歧，orchestrator 必须强制双方各写一遍，**最终由 orchestrator 给出裁决**。

### 辩题

> 用一句话陈述本辩论的核心争议（例：是否采用 PostgreSQL 分区表存储诊断记录？）

### 正方（Pro）

- **主张**：...
- **论据**（3 条以内）：
  1. ...
  2. ...
  3. ...
- **代表角色**：requirement-analyst / tech-architect / quality-guardian / security-reviewer / devops-reviewer（选一）
- **代表 agent**：...

### 反方（Con）

- **主张**：...
- **论据**（3 条以内）：
  1. ...
  2. ...
  3. ...
- **代表角色**：...
- **代表 agent**：...

### 事实核查（orchestrator 收集）

- ADR 引用：...
- 既有代码引用：...
- 性能/安全数据：...

### 裁决（orchestrator 写）

> **必须二选一**：采纳 / 暂缓 / 折中。

- **结论**：采纳 / 暂缓 / 折中
- **理由**：...
- **下一步动作**：
  - [ ] 更新 `evidence/02-tech-design.md`
  - [ ] 更新 `docs/spec/TDS-M*.md`
  - [ ] 新增 ADR（`docs/adr/ADR-<NNNN>-<slug>.md`）
  - [ ] 其它：...

## 4. 3 评审签字（A 档精简版）

| 评审角色 | 角色代表 | 签字 / 反对 / 弃权 |
|---|---|---|
| requirement-analyst | （业务） | |
| tech-architect | （技术） | |
| quality-guardian | （质量） | |
| security-reviewer | （安全，触发时） | |
| devops-reviewer | （部署，触发时） | |

> **铁律**：3 必签角色 + 触发的扩展角色全部签字或显式"弃权"方可推进到 Phase 4。
> 触发条件见本文件 §〇。

## 5. 决策请求

> 列出本文件需要 dispatcher / orchestrator 做出的具体决策。

- [ ] 是否进入 ATDD phase？
- [ ] 是否需要补做 ADR 草案？
- [ ] 是否调整 FR 编号？

## 参考

- 状态机：harness/workflow.yaml
- 上下文：harness/context/atdd-phase.md
- 角色协议：agents/harness/REVIEWERS.md
