---
name: harness-template-acceptance
description: >
  验收模板（Given-When-Then + 字段映射到 openapi.yaml）。
  Phase 4 ATDD 由 quality-guardian 填写；Phase 7 VERIFY 由 verifier 核验。
disable-model-invocation: true
---

# 验收模板（Acceptance Template）

> **使用方式**：每个 FR 一个 feature 文件，复制本模板填入 Given-When-Then。
> Phase 4 ATDD：quality-guardian 填正文；Phase 7 VERIFY：verifier 跑通后追加"已验证"标记。

## Frontmatter（强制）

```yaml
---
evidence_id: EV-<YYYY-MM-DD>-<fr_id>-AC
phase: ATDD
role: quality-guardian
author_agent: quality-guardian
created_at: <ISO 8601>
fr_id: <FR-XXX-XX>
schema_version: "1.0"
---
```

## 1. 观点

> 一句话总结本 FR 的可验收性（例：本 FR 通过 5 个 Gherkin 场景覆盖正常 / 边界 / 异常路径）。

## 2. 论据：Gherkin 场景

### 场景 1：正常路径

```gherkin
Feature: <FR-ID> <FR-Title>

  Scenario: <场景标题>
    Given <前置条件>
    When <用户/系统动作>
    Then <可观察结果>
    And <附加结果>
```

### 场景 2：边界路径

```gherkin
  Scenario: <边界标题>
    Given <边界前置条件>
    When <动作>
    Then <结果>
```

### 场景 3：异常路径

```gherkin
  Scenario: <异常标题>
    Given <异常前置>
    When <动作>
    Then <错误码/错误信息>
```

（场景数量按需扩展，但**至少覆盖正常 + 边界 + 异常**三类。）

## 3. 论据：字段映射到 openapi.yaml

> 每个验收点必须能映射到 `docs/architecture/api.yaml` 中的字段，否则视为"幻觉字段"。

| Given/Then 字段 | openapi.yaml 路径 | 类型 | 必填 |
|---|---|---|---|
| user_id | components.schemas.User.id | string | 是 |
| ... | ... | ... | ... |

## 4. 论据：依赖与外部状态

- **外部依赖**：数据库表 / Redis key / 第三方 API
- **前置数据**：seed 脚本或 fixture 文件路径
- **回归影响**：影响哪些已有 Gherkin 场景

## 5. 决策请求

- [ ] 该 FR 的验收用例是否完备？
- [ ] 是否需要补充 e2e / 集成测试？
- [ ] Phase 7 VERIFY 的核验口径是否清晰？

## Phase 7 核验追加（verifier 填）

```yaml
verified_at: <ISO 8601>
verified_by: verifier
result: PASS / FAIL
evidence_ref: evidence/05-acceptance.md
```

## 参考

- 状态机：harness/workflow.yaml
- 上下文：harness/context/phase-checklist.md
- openapi 真源：docs/architecture/api.yaml
- 上游 Skill：.cursor/skills/ad-tdd/SKILL.md（Phase 2 ATDD）
