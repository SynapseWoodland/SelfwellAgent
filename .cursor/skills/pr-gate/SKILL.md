---
name: pr-gate
description: >
  PR 守门 skill。当创建 PR、提交流前、或收到 PR review 评论时触发。
  CI 层检查见 .github/workflows/pr-gate.yml。
disable-model-invocation: false
---

# PR Gate — Human-Only 检查

## 触发条件

- 用户说"创建 PR"、"提交代码"、"提个 MR"、"帮我检查这个改动"

## 检查清单（Human-Only）

### 1. FR 关联提醒

检查本次改动关联了哪些 FR：
- 如果没有 FR 编号 → 输出提醒
- 如果有关联 → 在 PR description 中列出

### 2. 覆盖率提醒

提醒开发者检查改动模块的覆盖率：
- rules/ >= 90%
- agents/middleware/ >= 80%
- tools/ >= 70%
- 整体 >= 60%

### 3. CI 状态检查

检查 CI workflow 是否完整（ruff + mypy + pytest）

## 输出格式

完成检查后输出结构化总结。

## 边界说明

| 检查项 | CI 层 | Human 层 |
|--------|-------|----------|
| Commit 格式 | ✅ pr-gate.yml Gate 1 | — |
| FR 格式 | ✅ pr-gate.yml Gate 2 | 关联性提醒 |
| ATDD 存在 | ✅ pr-gate.yml Gate 3 (TODO) | — |
| ADR 冲突 | ✅ pr-gate.yml Gate 4 (TODO) | — |
| 覆盖率 | ✅ pr-gate.yml Gate 5 | 达标提醒 |
| PR 大小 | ✅ pr-gate.yml Gate 6 | — |
