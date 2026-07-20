# Harness Engine 5 种任务类型演示指南

> **创建日期**：2026-07-20
> **适用范围**：V2 状态机（16 phase）
> **Demo 目标**：展示如何启动 Harness 并完成 5 种任务类型

---

## 一、启动 Harness 的前提条件

### 1.1 必须的文件已就绪

| 文件 | 状态 | 验证命令 |
|------|:----:|---------|
| `harness/workflow-v2.yaml` | ✅ | `python harness/scripts/check_phase.py --list` |
| `harness/state/harness-state.json` | ✅ | 存在且有效 |
| `agents/harness/DISPATCHER.md` | ✅ | 协议完整 |
| `agents/harness/ORCHESTRATOR.md` | ✅ | 协议完整 |
| `agents/harness/EXECUTORS.md` | ✅ | 协议完整 |
| `agents/harness/REVIEWERS.md` | ✅ | 协议完整 |
| `harness/scripts/check_phase.py` | ✅ | L0-L1 PASS |
| `harness/evidence/01-requirement.md` | ✅ | PRD 已通过 |

### 1.2 启动命令

用户只需要说一句话：

```
"按 Harness 跑 [任务描述]"
```

Harness Dispatcher 会自动：
1. 读取 `harness/state/harness-state.json`
2. 读取 `harness/workflow-v2.yaml`
3. 根据任务类型推断 task_type
4. 输出 next_agent 指令

---

## 二、5 种任务类型总览

| task_type | 中文名 | 适用场景 | Phase 数量 |
|-----------|--------|---------|:----------:|
| `feature` | 完整功能开发 | 新功能、复杂需求 | 15 |
| `bugfix` | Bug 修复 | 线上故障、缺陷修复 | 5 |
| `refactor` | 代码重构 | 提升代码质量 | 5 |
| `doc-fix` | 文档修复 | 修复文档错误 | 3 |
| `perf-optimize` | 性能优化 | 性能调优、慢查询 | 6 |

### 2.1 Phase 流程对比图

```
feature:    PRD → ARCH_DESIGN → PRE_MORTEM → ATDD → PLAN → CODE → VERIFY → SECURITY_TEST → DEPLOY → REGRESSION → SIGN_OFF → DATA_REPLAY → INCIDENT_RESPONSE → OPS_LOOP → SKILL_UPDATE
bugfix:                                    [CODE] → VERIFY → DEPLOY → REGRESSION → SIGN_OFF
refactor:                                              [PLAN] → CODE → VERIFY → REGRESSION → SIGN_OFF
doc-fix:                                               [CODE] → VERIFY → SIGN_OFF
perf-optimize:                                         [PLAN] → CODE → VERIFY → DEPLOY → REGRESSION → SIGN_OFF
```

---

## 三、每种任务类型的完整示例

### 3.1 Feature：完整功能开发

#### 用户输入
```
"按 Harness 跑，做一个「用户收藏夹」功能"
```

#### Dispatcher 路由
```json
{
  "task_type": "feature",
  "next_agent": "requirement-analyst",
  "phase": "PRD",
  "context_to_load": "harness/context/phase-checklist.md",
  "evidence_to_write": "harness/evidence/01-requirement.md"
}
```

#### 完整流程（15 个 Phase）

| Phase | Agent | 产出 | Exit Criteria |
|-------|-------|------|--------------|
| **PRD** | requirement-analyst | `01-requirement.md` | evidence 存在 + signed + fr_refs |
| **ARCH_DESIGN** | tech-architect | `02-tech-design.md` | evidence 存在 + signed + adr_refs |
| **PRE_MORTEM** | 5 reviewer → orchestrator | `03-pre-mortem.md` | 3 必签 + 2 触发式签字 |
| **ATDD** | quality-guardian | `04-atdd.md` | evidence 存在 + Gherkin 场景 |
| **PLAN** | plan-generator | `05-plan.md` | evidence 存在 + signed + fr_refs |
| **CODE** | developer | `06-code.md` + 代码 | evidence 存在 + pytest unit PASS |
| **VERIFY** | verifier | `07-verify.md` | L0-L6 全 PASS |
| **SECURITY_TEST** | security-reviewer | `08-security-test.md` | bandit 无 S/F |
| **DEPLOY** | deployer | `09-deploy.md` | 部署成功 |
| **REGRESSION** | tester | `10-regression.md` | Golden Set 跌幅 ≤ 5% |
| **SIGN_OFF** | orchestrator | `11-signoff.md` | 5 评审签字 |
| **DATA_REPLAY** | requirement-analyst | `12-data-replay.md` | replay_session_id 生成 |
| **INCIDENT_RESPONSE** | deployer | `13-incident-response.md` | 故障已处理 |
| **OPS_LOOP** | tester | `14-ops-loop.md` | A/B 测试达标 |
| **SKILL_UPDATE** | quality-guardian | `15-skill-update.md` | lesson 沉淀 |

#### 示例输出
```bash
# 启动 feature
> "按 Harness 跑，做用户收藏夹功能"
✓ Dispatcher 分析：task_type=feature
✓ 进入 PRD phase
✓ 调用 requirement-analyst agent
✓ 产出 evidence/01-requirement.md

# 自动推进
PRD → ARCH_DESIGN → PRE_MORTEM → ATDD → PLAN → CODE → ...
```

---

### 3.2 Bugfix：Bug 修复

#### 用户输入
```
"按 Harness 跑，修复 M1 微信登录的 unionid 为空的 bug"
```

#### Dispatcher 路由
```json
{
  "task_type": "bugfix",
  "next_agent": "developer",
  "phase": "CODE",
  "context_to_load": "harness/context/phase-checklist.md",
  "evidence_to_write": "harness/evidence/06-code.md"
}
```

> **注意**：bugfix 从 CODE 开始，跳过 PRD/ARCH_DESIGN/PRE_MORTEM/ATDD/PLAN

#### 完整流程（5 个 Phase）

| Phase | Agent | 产出 | Exit Criteria |
|-------|-------|------|--------------|
| **CODE** | developer | `06-code.md` + 修复代码 | evidence 存在 + pytest PASS |
| **VERIFY** | verifier | `07-verify.md` | L0-L6 全 PASS |
| **DEPLOY** | deployer | `09-deploy.md` | 部署成功 |
| **REGRESSION** | tester | `10-regression.md` | 相关测试 PASS |
| **SIGN_OFF** | orchestrator | `11-signoff.md` | 评审签字 |

#### 示例输出
```bash
# 启动 bugfix
> "按 Harness 跑，修复微信登录 unionid 为空 bug"
✓ Dispatcher 分析：task_type=bugfix
✓ 从 CODE phase 开始（跳过 PRD/ARCH/PRE_MORTEM/ATDD/PLAN）
✓ 调用 developer agent
✓ 产出 evidence/06-code.md

# 自动推进
CODE → VERIFY → DEPLOY → REGRESSION → SIGN_OFF → DONE
```

---

### 3.3 Refactor：代码重构

#### 用户输入
```
"按 Harness 跑，重构 diagnosis_service 的冗长方法"
```

#### Dispatcher 路由
```json
{
  "task_type": "refactor",
  "next_agent": "plan-generator",
  "phase": "PLAN",
  "context_to_load": "harness/context/phase-checklist.md",
  "evidence_to_write": "harness/evidence/05-plan.md"
}
```

> **注意**：refactor 从 PLAN 开始，跳过 PRD/ARCH_DESIGN/PRE_MORTEM/ATDD

#### 完整流程（5 个 Phase）

| Phase | Agent | 产出 | Exit Criteria |
|-------|-------|------|--------------|
| **PLAN** | plan-generator | `05-plan.md` | 重构步骤 + 回滚方案 |
| **CODE** | developer | `06-code.md` + 重构代码 | evidence 存在 + 测试 PASS |
| **VERIFY** | verifier | `07-verify.md` | L0-L6 全 PASS |
| **REGRESSION** | tester | `10-regression.md` | 全量回归 PASS |
| **SIGN_OFF** | orchestrator | `11-signoff.md` | 评审签字 |

#### 示例输出
```bash
# 启动 refactor
> "按 Harness 跑，重构 diagnosis_service"
✓ Dispatcher 分析：task_type=refactor
✓ 从 PLAN phase 开始（跳过 PRD/ARCH/PRE_MORTEM/ATDD）
✓ 调用 plan-generator agent
✓ 产出 evidence/05-plan.md（含重构步骤 + 回滚方案）

# 自动推进
PLAN → CODE → VERIFY → REGRESSION → SIGN_OFF → DONE
```

---

### 3.4 Doc-Fix：文档修复

#### 用户输入
```
"按 Harness 跑，修复 API 文档中错误的状态码描述"
```

#### Dispatcher 路由
```json
{
  "task_type": "doc-fix",
  "next_agent": "developer",
  "phase": "CODE",
  "context_to_load": "harness/context/phase-checklist.md",
  "evidence_to_write": "harness/evidence/06-code.md"
}
```

> **注意**：doc-fix 从 CODE 开始，只走 3 个 phase

#### 完整流程（3 个 Phase）

| Phase | Agent | 产出 | Exit Criteria |
|-------|-------|------|--------------|
| **CODE** | developer | `06-code.md` + 修复文档 | evidence 存在 + 文档格式检查 |
| **VERIFY** | verifier | `07-verify.md` | 文档一致性检查 PASS |
| **SIGN_OFF** | orchestrator | `11-signoff.md` | 评审签字 |

#### 示例输出
```bash
# 启动 doc-fix
> "按 Harness 跑，修复 API 文档错误的状态码"
✓ Dispatcher 分析：task_type=doc-fix
✓ 从 CODE phase 开始（最短路径）
✓ 调用 developer agent
✓ 产出 evidence/06-code.md

# 自动推进
CODE → VERIFY → SIGN_OFF → DONE
```

---

### 3.5 Perf-Optimize：性能优化

#### 用户输入
```
"按 Harness 跑，优化打卡接口的响应时间，目前 P95 是 500ms，需要降到 100ms"
```

#### Dispatcher 路由
```json
{
  "task_type": "perf-optimize",
  "next_agent": "plan-generator",
  "phase": "PLAN",
  "context_to_load": "harness/context/phase-checklist.md",
  "evidence_to_write": "harness/evidence/05-plan.md"
}
```

> **注意**：perf-optimize 从 PLAN 开始，需要 DEPLOY 验证实际效果

#### 完整流程（6 个 Phase）

| Phase | Agent | 产出 | Exit Criteria |
|-------|-------|------|--------------|
| **PLAN** | plan-generator | `05-plan.md` | 优化方案 + 性能指标目标 |
| **CODE** | developer | `06-code.md` + 优化代码 | evidence 存在 + 性能测试 PASS |
| **VERIFY** | verifier | `07-verify.md` | L0-L6 全 PASS |
| **DEPLOY** | deployer | `09-deploy.md` | 预发性能验证 |
| **REGRESSION** | tester | `10-regression.md` | 全量回归 PASS |
| **SIGN_OFF** | orchestrator | `11-signoff.md` | 评审签字 |

#### 示例输出
```bash
# 启动 perf-optimize
> "按 Harness 跑，优化打卡接口 P95 从 500ms 降到 100ms"
✓ Dispatcher 分析：task_type=perf-optimize
✓ 从 PLAN phase 开始
✓ 调用 plan-generator agent
✓ 产出 evidence/05-plan.md（含优化方案 + 性能目标）

# 自动推进
PLAN → CODE → VERIFY → DEPLOY → REGRESSION → SIGN_OFF → DONE
```

---

## 四、Harness 工作流演示脚本

### 4.1 创建新 run

```bash
# 方式 1：完整功能
> "按 Harness 跑，做用户收藏夹"

# 方式 2：Bug 修复
> "按 Harness 跑，修复 XX bug"

# 方式 3：代码重构
> "按 Harness 跑，重构 XX 模块"

# 方式 4：文档修复
> "按 Harness 跑，修复 XX 文档"

# 方式 5：性能优化
> "按 Harness 跑，优化 XX 接口性能"
```

### 4.2 检查当前状态

```bash
# 列出所有 phase
python harness/scripts/check_phase.py --list

# 检查 PRD
python harness/scripts/check_phase.py PRD --verbose

# 检查所有 phase
python harness/scripts/check_phase.py --all

# 查看状态文件
cat harness/state/harness-state.json
```

### 4.3 中断与恢复

```bash
# 中断当前 phase
> "暂停，先看看 PRD 的 evidence"
✓ Dispatcher 检查：interrupt_budget > 0
✓ 记录 interrupted_phase = PRD
✓ 进入 INTERRUPT_REVIEW

# 恢复执行
> "继续"
✓ Dispatcher 恢复 interrupted_phase = PRD
✓ 继续执行
```

---

## 五、快速参考表

| 任务 | 用户说 | task_type | 起点 | Phase 数 |
|------|--------|-----------|------|:--------:|
| 新功能 | "按 Harness 跑，做收藏夹" | `feature` | PRD | 15 |
| Bug 修复 | "按 Harness 跑，修复 XX bug" | `bugfix` | CODE | 5 |
| 重构 | "按 Harness 跑，重构 XX 模块" | `refactor` | PLAN | 5 |
| 文档修复 | "按 Harness 跑，修复 XX 文档" | `doc-fix` | CODE | 3 |
| 性能优化 | "按 Harness 跑，优化 XX 接口" | `perf-optimize` | PLAN | 6 |

---

## 六、常见问题

### Q1: 如何跳过已完成的 phase？
```
> "按 Harness 跑，做 XX，跳过 PRD 和 ARCH_DESIGN"
✓ Dispatcher 在 state.json 中标记跳过状态
✓ 直接从 PRE_MORTEM 开始
```

### Q2: 中断 budget 耗尽怎么办？
```
✓ interrupt_budget = 0 时，Dispatcher 返回 AskUser
✓ 用户选择：授权额外中断 / 强制继续
```

### Q3: 如何查看当前进度？
```bash
cat harness/state/harness-state.json
# 查看 current_phase, exit_criteria_met, phase_history
```

### Q4: 如何验证 phase 完成？
```bash
python harness/scripts/check_phase.py <phase_id> --verbose
# 例如：python harness/scripts/check_phase.py PRD --verbose
```

---

## 七、下一步

- 📖 详细 phase 清单：[`harness/context/phase-checklist.md`](phase-checklist.md)
- 📋 Evidence 规范：[`harness/evidence/README.md`](evidence/README.md)
- 🔧 检查脚本：[`harness/scripts/check_phase.py`](scripts/check_phase.py)
