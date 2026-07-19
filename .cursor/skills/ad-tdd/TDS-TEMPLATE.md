# TDS 技术设计文档模板

> **命名说明**：TDS = Technical Design Specification（技术设计文档）
> **对齐阿里 Harness**：本模板对齐 `docs/skills/ad-tdd/SKILL.md` Phase 1 Architecture 阶段

## 文件命名

`docs/spec/TDS-<编号>-<标题>.md`

## 文档结构

```markdown
# TDS-<编号> <标题>

> **id**: TDS-<编号>
> **title**: <标题>
> **version**: V1.0
> **status**: Draft | Accepted | Locked
> **created**: <日期>
> **authors**: <作者>

## 1. 背景

为什么需要这个功能？解决了什么问题？关联哪些业务场景？

## 2. 目标

1. 目标 1
2. 目标 2

## 3. 约束

- 技术约束（如：必须兼容 Python 3.12+）
- 架构约束（如：不得违反 ADR-XXXX）
- 时间/范围约束

## 4. FR 可追溯性

| FR 编号 | 描述 | 来源 |
|---------|------|------|
| <FR-01> | <描述> | PRD §1.x |

## 5. ATDD 验收标准

> **对应文件**：`harness/atdd/TDS-<编号>-AC.md`

详见 ATDD 验收标准文档。

## 6. 实施计划

### Phase 1：<阶段名称>

**目标**：<本阶段目标>

#### 验收标准（Acceptance Criteria）

| # | 描述 | 验证方式 | 测试文件 |
|---|------|----------|----------|
| AC-1.1 | <标准描述> | <如何验证> | `tests/unit/test_xxx.py` |
| AC-1.2 | <标准描述> | <如何验证> | `tests/integration/test_xxx.py` |

#### 实施步骤

1. 步骤 1
2. 步骤 2

#### 测试场景

##### Smoke Test（冒烟测试）

- [ ] **场景 1**：<描述>
  - 输入：<>
  - 预期：<>

##### Full Regression（全量回归）

- [ ] **场景 2**：<描述>
  - 输入：<>
  - 预期：<>

---

### Phase 2：<阶段名称>

（同上结构）

---

## 7. 全量测试矩阵

| 场景 | 类型 | 优先级 | 对应 Phase |
|------|------|--------|------------|
| <场景名> | Smoke / Full | P0 / P1 / P2 | Phase 1 |
| <场景名> | Smoke / Full | P0 / P1 / P2 | Phase 2 |

## 8. 风险与依赖

| 风险/依赖 | 影响 | 缓解措施 |
|-----------|------|----------|
| <风险> | <影响> | <缓解> |

## 9. 退出标准

- [ ] 所有验收标准已实现
- [ ] 所有 Smoke Test PASS
- [ ] 所有 Full Regression PASS
- [ ] 覆盖率达标
- [ ] AI self-review PASS
- [ ] Commit message 符合规范
```

## 10. ATDD 文件模板

对应的 ATDD 验收标准文件放在 `harness/atdd/TDS-<编号>-AC.md`：

```markdown
# TDS-<编号>: <标题> - 验收标准

> **对应 TDS**: `docs/spec/TDS-<编号>-<标题>.md`
> **版本**: V1.0
> **状态**: Draft

## Feature: <功能名>

### Scenario: <场景名>
```gherkin
Given <前置条件>
When <操作>
Then <预期结果>
```

### Scenario: <边界场景>
```gherkin
Given <边界条件>
When <操作>
Then <预期结果>
```

### Scenario: <异常场景>
```gherkin
Given <异常条件>
When <操作>
Then <预期结果>
```
```
