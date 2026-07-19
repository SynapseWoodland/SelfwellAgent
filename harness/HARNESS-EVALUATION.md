# SelfwellAgent Harness Engineering 全面评估报告

> **评估日期**: 2026-07-18
> **评估者**: AI 子 Agent（第三方批判性视角）
> **评估模式**: **一人 AI 开发模式**（单人全链路自动化优先）
> **评估方法**: 源码逐文件批判性审查 + 业界最佳实践对比（AutoGen / LangGraph / CrewAI / Harness.io）
> **评估范围**: `agents/harness/` + `.cursor/skills/harness-*/` + `harness/` + `ad-tdd/SKILL.md`
> **已知前提**: 已存在一份评估（HARNESS-EVALUATION.md 33887 字节）和 GAP-ANALYSIS.md（13203 字节），本报告为独立重新评估，聚焦一人模式核心诉求并补全新发现。

---

## 执行摘要

当前 Harness 工程体系**协议文档层成熟度约 82%**，但**落地执行层成熟度仅约 12%**。

**一人模式核心矛盾**：用户说"继续完成剩余所有步骤"，期望机器自动跑完全流程。但当前所有 phase 之间都需要人介入说"下一步"，状态机是"人驱动"而非"事件/自动驱动"，核心场景**完全不可行**。

**最关键阻断项**：

1. **从未跑通过一个真实 FR**（协议写完但零实战验证）
2. **状态机无自动推进机制**（Dispatcher 依赖人触发）
3. **evidence 目录只有 .gitkeep**（真实运行产物完全缺失）
4. **exit_criteria 全为占位符**（无法判断 phase 是否真正完成）
5. **ATDD 目录存在但无人执行**（13 份文件从未被 pytest 执行）

**与 AutoGen/LangGraph 的最大差距**：两者有状态机自动推进（LangGraph）和多 Agent 并行（AutoGen），SelfwellAgent 的设计理念接近 Harness.io（企业级 CI/CD），但实现停留在"协议文档"层面，从未跑通。

---

## 一、架构评估

### 1.1 模块解耦程度

| 组件 | 职责清晰度 | 耦合度 | 评估 |
|------|-----------|--------|------|
| DISPATCHER | 状态机路由（只读 state.json + workflow-v2.yaml） | 低 | ✅ 优秀 |
| ORCHESTRATOR | 多角色合成（只读 evidence 写 synthesis） | 低 | ✅ 良好 |
| REVIEWERS | 单角色评审（各读己所需） | 低 | ✅ 良好 |
| EXECUTORS | 执行开发/测试/部署（各司其职） | 低 | ✅ 良好 |

**优点**：

- 4 份协议通过 `evidence/*.md` 路径对齐，单文件改动不强制其他三份同步
- frontmatter 8 字段统一约束所有 evidence 文件格式
- `interrupt_budget` 和 `replay_session_id` 字段在所有层保持一致
- 所有协议文件 frontmatter 标注 `contains_business_rules: false` + `scope: harness-protocol`

**问题**：

| 问题 #C1 | exit_criteria 全为占位符，状态机无法判断 phase 完成 |
|----------|---------------------------------------------------|
| **严重程度** | 🔴 **Critical** |
| **发现位置** | `workflow-v2.yaml` L18-144，所有 16 个 phase 的 `exit_criteria: [false, false, false]` |
| **类型** | 架构 |
| **描述** | 所有 16 个 phase 的 `exit_criteria` 全部是 `[false, false, false]` 占位符。没有一个 phase 实现了真实的退出条件判定逻辑。Dispatcher 无法判断"当前 phase 是否真正完成"，只能依赖人读 evidence 文件后手动说"下一步"。状态机在**机器可执行性**上完全失效。 |
| **影响** | 状态机断链——即使evidence文件存在，Dispatcher 也不知道 phase 是否完成。核心场景"继续完成剩余所有步骤"被此问题完全阻断。 |
| **根因** | 设计时把 `exit_criteria` 字段写进了 workflow-v2.yaml，但从未实现真实判定逻辑。 |
| **建议** | ① 定义每个 phase 的具体 check 命令（如 `evidence/01-requirement.md` 是否存在 + frontmatter `signed: true`）；② 用 grep 命令自动化验证（如 `grep "signed: true" harness/evidence/01-requirement.md`）；③ 全部为 false 时阻塞推进。在 harness-dispatcher SKILL.md 中实现这些检查。 |
| **优先级** | **P0** |

| 问题 #C2 | evidence 目录只有 .gitkeep，真实运行产物完全缺失 |
|----------|--------------------------------------------------|
| **严重程度** | 🔴 **Critical** |
| **发现位置** | `harness/evidence/` 目录内容：仅 `.gitkeep` 一个文件 |
| **类型** | 架构 |
| **描述** | 尽管有完整的 evidence 模板（17 个 evidence 文件模板）、命名规范、frontmatter schema，但 evidence 目录中没有任何真实的运行产物。这意味着：没有任何一个 FR 的 requirement / tech-design / pre-mortem / code 产物被实际写入过。 |
| **影响** | ① 状态机无法通过 evidence 文件判断 phase 完成（因为没有 evidence）；② 文档体系无法证明"Harness 被真实使用过"；③ 所有 phase 间衔接都依赖人读人写。 |
| **根因** | checklist W4 P1 §2.3.1 "跑 1 个 pilot FR 过 V2 全部 16 phase" 状态为 ⏳（待启动），从未执行。 |
| **建议** | 立即跑一个最小 FR（如 ATDD-M1 "微信登录"），强制写完至少 5 个核心 evidence 文件（01-05），commit 进仓库作为 baseline。 |
| **优先级** | **P0** |

| 问题 #C3 | 5 个 Skill 文件不满足 check.sh ≤100 行约束 |
|----------|------------------------------------------------|
| **严重程度** | 🟠 **High** |
| **发现位置** | `harness/scripts/check.sh` L48-62（行数校验） |
| **类型** | 架构 |
| **描述** | check.sh L48-62 对 `.cursor/skills/harness-*/SKILL.md` 做行数 ≤100 的校验。但：harness-dispatcher（109 行）、harness-business-interview（289 行）**已经超出 100 行限制**。check.sh 会 exit 2，但这个校验从未被真正执行过（harness-ci.yml 的 path filter 依赖 harness/ 变更才触发，Skill 文件修改不会触发）。 |
| **影响** | CI 兜底失效——即使 Skill 超行数，CI 也不会 catch 到。 |
| **根因** | check.sh 是 W1 P0 新增的兜底机制，但 harness-business-interview 和更新后的 harness-dispatcher 是在 check.sh 之后创建的，没有同步更新行数上限或豁免列表。 |
| **建议** | ① 对 harness-business-interview/SKILL.md 设置豁免（业务问答专用 skill，复杂度天然高）；② 将行数上限改为 150 行（对 harness-dispatcher）；③ 在 check.sh 中用白名单而非通用 glob。 |
| **优先级** | **P1** |

### 1.2 状态管理

| 维度 | 评估 | 详情 |
|------|------|------|
| Schema 完整性 | ✅ | harness-state.json schema 定义了完整的 12 个字段，包括 interrupt_stack / phase_history / run_metadata |
| 迁移兼容性 | ✅ | V1.6 → V2 有默认值填充逻辑（harness-state.json schema §三） |
| 写入权限隔离 | ⚠️ | dispatcher/orchestrator 写 state.json，但 orchestrator 的 phase_history 写入权限与 dispatcher 的 current_phase 写入有潜在竞争 |
| 持久化 | 🔴 | state.json 存于 docs/ 目录，没有 PostgreSQL 表记录。无 audit trail，run_id 无法追溯。 |

### 1.3 容错机制

| 机制 | 状态 | 评估 |
|------|------|------|
| 单点故障处理 | ❌ 无 | 任何 phase 失败后无回退机制 |
| Agent 执行失败恢复 | ❌ 无 | 没有 retry 逻辑 |
| 中断栈 | ✅ 有 | interrupt_stack 字段定义完整 |
| 嵌套中断 | ✅ 有 | interrupt_stack 支持嵌套 |
| 预算耗尽升级 | ✅ 有 | AskUser 升级机制 |
| Phase 回退 | ❌ 无 | 单向状态机，无法退回上一个 phase |

---

## 二、流程评估

### 2.1 端到端流程完整性

```
PRD → ARCH_DESIGN → PRE_MORTEM → ATDD → PLAN → CODE → VERIFY
→ SECURITY_TEST → DEPLOY → REGRESSION → SIGN_OFF
→ DATA_REPLAY → PRD(循环)
```

**V2 覆盖 16 phase，但存在严重的"纸上流程"问题**：

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 阶段数量 | ✅ | 16 phase 覆盖完整开发周期（需求→上线→运营→反馈） |
| 阶段边界 | ⚠️ | PRD → ARCH_DESIGN 边界模糊（TDS 应在哪个 phase 生成？） |
| V2 新增 phase 落地 | 🔴 | 6 个新 phase 全部未落地（checklist W12 P2 0/13 完成） |
| 文档到代码的转换 | ⚠️ | ATDD Gherkin 无法自动转为 pytest 测试用例（需要人工桥接） |
| 真实 FR 跑通 | 🔴 | **0 个真实 run 记录** |

| 问题 #C4 | 没有一个真实 FR 跑通过全流程 |
|----------|------------------------------|
| **严重程度** | 🔴 **Critical** |
| **发现位置** | `harness/evidence/`（仅 .gitkeep）+ `harness/checklist.md` W4 P1 §2.3.1 状态 ⏳ |
| **类型** | 流程 |
| **描述** | 所有协议文件齐全（35 个文件），但 evidence 目录没有任何真实产物。checklist W4 P1 §2.3.1 "跑 1 个 pilot FR 过 V2 全部 16 phase" 状态为 ⏳（待启动）。这是最核心的架构-实现断层。 |
| **影响** | 所有协议设计无法得到实战验证。exit_criteria 是否合理、phase 划分是否顺畅、reviewer 协作是否有摩擦——全部未知。 |
| **根因** | 缺少"第一个吃螃蟹的人"。团队在完善协议，但没有人真正用起来。 |
| **建议** | ① 立即选一个最小 FR（如 ATDD-M1 "微信登录"），强制走完 V1.6 全流程；② 在走完第一个 FR 后，复盘所有断点并更新协议；③ 将第一个 FR 的 evidence 全部 commit 进仓库作为 baseline。 |
| **优先级** | **P0** |

### 2.2 阶段间衔接

| 问题 #C5 | 核心场景"继续完成剩余所有步骤"存在多个断点 |
|----------|--------------------------------------------|
| **严重程度** | 🔴 **Critical** |
| **发现位置** | `harness-dispatcher/SKILL.md` §二 + `DISPATCHER.md` §六 |
| **类型** | 流程 |
| **描述** | 用户已有 PRD + SRS，说"继续完成剩余所有步骤"，期望：自动生成 SDS/TDS → 执行 ATDD → 开发 → 测试 → commit。但当前流程有以下断点：<br><br>**断点 1**：Dispatcher 不知道"哪些 phase 已完成"——state.json 的 exit_criteria 全部是 `[false, false, false]` 占位符，无法判断。<br><br>**断点 2**：SDS/TDS 生成依赖 tech-architect agent，但没有"批量续跑"机制——人必须每个 phase 说一次"下一步"。<br><br>**断点 3**：ATDD 生成后没有自动触发 TDD 循环。<br><br>**断点 4**：CODE 完成后需要人工触发 VERIFY → DEPLOY → REGRESSION。<br><br>**整个流水线不是连续自动的，需要人在每个 phase 之间说"下一步"。** |
| **影响** | "一键续跑"场景无法实现。用户每走一步都要介入，无法真正实现"说一句话，机器自动跑完全流程"。 |
| **根因** | 状态机设计是"人驱动"而非"事件驱动"。没有自动推进机制。Dispatcher 的决策完全依赖"人判断当前 phase 已完成 → 说下一步 → Dispatcher 才读 state.json → 决定 next_agent"。 |
| **建议** | ① 实现 `--resume-from <phase>` flag：给定一个 state.json，自动识别当前 phase 并续跑；② 实现 `--batch` mode：给定 PRD + SRS，自动跑完 PRD→ARCH_DESIGN→PRE_MORTEM→ATDD→PLAN→CODE→VERIFY→DEPLOY→REGRESSION→SIGN_OFF 全链路；③ 用 GitHub Actions 或 cron job 支持后台自动推进。 |
| **优先级** | **P0** |

### 2.3 ATDD 可执行性

| 问题 #C6 | ATDD 无法自动转为可执行 pytest 测试 |
|----------|-----------------------------------|
| **严重程度** | 🟠 **High** |
| **发现位置** | `harness/atdd/ATDD-M1-AC.md`（Gherkin 格式）+ `EXECUTORS.md` §2.3 L54-64（verifier 跑 pytest，但 ATDD 不是 pytest） |
| **类型** | 流程 |
| **描述** | ATDD-M1-AC.md 使用 Gherkin 语言（Given-When-Then）编写验收测试。但 verifier（EXECUTORS.md §2.3）运行的是 `pytest tests/{integration,e2e,smoke}` ——Gherkin 文件不是 pytest 可执行格式。两者之间缺少"ATDD → pytest 测试用例"的自动转换步骤。atdd/ 目录有 13 份文件，但从未被 pytest 执行过。 |
| **影响** | ATDD 作为验收标准，但无法自动验证。开发者必须人工将 Given-When-Then 翻译成 pytest 测试，导致 ATDD 形同虚设。一人模式下，这额外增加了人工介入成本。 |
| **根因** | Gherkin 是产品/QA 可读格式，pytest 是开发者可执行格式，两者之间没有建立标准转换管道。 |
| **建议** | ① 使用 `pytest-bdd` 插件让 pytest 直接执行 Gherkin 文件；② 或在 verifier 阶段前增加"ATDD 翻译"步骤；③ 至少在 ad-tdd SKILL.md 中明确 ATDD → pytest 的转换规范。 |
| **优先级** | **P1** |

---

## 三、Agent 角色分配评估（一人模式视角）

### 3.1 角色定义清晰度

| 角色 | 职责边界 | 清晰度 | 一人模式评估 |
|------|---------|--------|-------------|
| requirement-analyst | PRD/SRS → FR 拆分 | ✅ | ⚠️ 一人模式下自己评审自己，意义有限 |
| tech-architect | 方案设计 → TDS | ✅ | ⚠️ 一人模式下自己做架构，容易陷入"自我审查" |
| quality-guardian | ATDD + 质量门禁 | ✅ | ✅ 有用，机器强制执行比人工更可靠 |
| security-reviewer | 安全评审（触发式） | ✅ | ✅ 有用 |
| devops-reviewer | 部署评审（触发式） | ✅ | ✅ 有用 |
| plan-generator | 实施计划 | ✅ | ⚠️ 一人模式下可与 developer 合并 |
| developer | CODE + TDD | ✅ | ✅ 核心执行者 |
| verifier | L0-L6 验证（只检不修） | ✅ | ✅ 关键分离，防止自审自查 |
| deployer | 部署 | ✅ | ✅ 有用 |
| tester | Golden Set 回归 | ✅ | ✅ 有用 |
| orchestrator | 合成（仅 PRE_MORTEM/SIGN_OFF） | ✅ | ⚠️ 一人模式下 5 reviewer → orchestrator 合成流程过于繁琐 |
| Dispatcher | 路由（只读不写） | ✅ | ✅ 核心调度者 |

### 3.2 一人模式下的角色效率问题

| 问题 #M1 | PRE_MORTEM 5 个 reviewer 串行调用对一人模式过于繁琐 |
|----------|------------------------------------------------------|
| **严重程度** | 🟡 **Medium** |
| **发现位置** | `workflow-v2.yaml` L34（dispatch.mode=serial）+ `harness-dispatcher/SKILL.md` |
| **类型** | 角色 |
| **描述** | PRE_MORTEM 要求 5 个 reviewer 串行调用（DISPATCHER.md §四："5 reviewer → orchestrator → ATDD"）。在一人模式下，这意味着：同一个人的 5 个"视角"被强制串行执行，每次都要读 phase-checklist、产出 evidence、再等 orchestrator 合成。这对单人开发来说成本过高（context 切换 + evidence 写作 + orchestrator 合成全要跑）。 |
| **影响** | 一人模式下 PRE_MORTEM 变成沉重的仪式负担，可能导致用户绕过 PRE_MORTEM 直接进入 ATDD/CODE。 |
| **根因** | 5 reviewer 串行是为多人团队设计的防漏机制（防止单点遗漏），在一人模式下变成冗余。 |
| **建议** | ① 为一人模式提供"快速 PRE_MORTEM"：requirement-analyst 一个角色完成所有 5 问自审，直接签字；② 保留完整 5 reviewer 流程作为可选模式；③ 在 harness-dispatcher SKILL.md 中增加 `--single-person` flag，自动走快速路径。 |
| **优先级** | **P2** |

| 问题 #M2 | orchestrator 合成在一人模式下增加不必要的环节 |
|----------|----------------------------------------------|
| **严重程度** | 🟡 **Medium** |
| **发现位置** | `workflow-v2.yaml` L34（L99）PRE_MORTEM + SIGN_OFF 的 `synthesis_agent: orchestrator` |
| **类型** | 角色 |
| **描述** | 一人模式下，同一个人产出的 5 个 reviewer evidence，需要再经 orchestrator 合成一份 synthesis。这增加了：① orchestrator 的合成时间；② 额外的 evidence 文件（synthesis.md）；③ 上下文切换成本。 |
| **影响** | 流水线摩擦增加，但合成产物的价值有限（因为只有一个人在主导）。 |
| **根因** | orchestrator 是为多人协作设计的合成机制。 |
| **建议** | 一人模式下，orchestrator 合成变为自动摘要生成（而非对抗性观点合并），可考虑将合成成本降低。 |
| **优先级** | **P2** |

---

## 四、中断与人机交互评估（一人模式精简版）

### 4.1 中断触发条件

| 评估项 | 是否覆盖 | 一人模式评估 |
|--------|---------|-------------|
| 需求歧义 | ✅ | ✅ interrupt_budget 机制 |
| 技术选型争议 | ✅ | ✅ INTERRUPT_REVIEW phase |
| 安全/合规风险 | ✅ | ✅ security-reviewer 触发式 |
| 测试失败且 Agent 无法修复 | ⚠️ | ⚠️ 没有明确升级机制 |
| Prompt 改动导致 Golden Set 失败 | ✅ | ✅ PR-Gate 拒绝 |
| **LLM 预算超限** | ❌ | ❌ 无明确触发（一人模式同样受影响） |

| 问题 #M3 | LLM 预算超限无明确中断机制 |
|----------|--------------------------|
| **严重程度** | 🟡 **Medium** |
| **发现位置** | `workflow-v2.yaml` + `harness/state/harness-state.json`（无 budget 监控字段） |
| **类型** | 中断 |
| **描述** | V3 §1.1 规定 LLM 月预算 ¥700，但 harness-state.json 中没有任何字段记录当前 run 的 LLM 消耗。interrupt_budget 只追踪"人类追问次数"，不追踪"LLM token 消耗"。一人模式下 CODE 阶段 LLM 调用超出预算时，没有明确的 phase 中断和升级机制。 |
| **影响** | LLM 预算超限可能导致超额支出。 |
| **建议** | ① 在 state.json 中增加 `llm_cost_yuan` 字段；② 当 llm_cost_yuan > 预算阈值时，在 CODE/VERIFY 阶段自动触发 AskUser 确认。 |
| **优先级** | **P2** |

### 4.2 恢复流程

| 评估项 | 状态 | 一人模式评估 |
|--------|------|-------------|
| 中断栈保存 | ✅ | ✅ interrupt_stack 字段完整 |
| 恢复后继续执行 | ✅ | ✅ resume_from 字段 |
| 预算耗尽升级 | ✅ | ✅ AskUser 机制 |
| interrupt_log 记录 | ✅ | ✅ harness-business-interview 定义了 schema |

---

## 五、文档质量评估

### 5.1 文档完整性

| 文档类型 | 路径 | 状态 | 一人模式评估 |
|----------|------|------|-------------|
| PRD | `docs/PRD/Selfwell-PRD-V1.1.md` | ✅ 存在 | ✅ 完整 |
| SRS | `docs/requirements/SELFWELL-MVP-SRS.md` | ✅ **存在** | ✅ 680+ 行完整 |
| SDS | 无 | ❌ | ❌ 文档体系没有 SDS 文档类型，只有 TDS |
| TDS | `docs/spec/TDS-*.md` | ✅ 存在 | ✅ 13+ 份 |
| ATDD | `harness/atdd/ATDD-*.md` | ✅ **13 份** | ⚠️ **存在但从未被执行** |
| evidence | `harness/evidence/` | ❌ 仅 .gitkeep | 🔴 **无真实产物** |
| phase context | `harness/context/` | ✅ 完整 | ✅ 7 份含 phase-checklist.md |

> **重要更正**：SRS 文件**确实存在**于 `docs/requirements/SELFWELL-MVP-SRS.md`（680+ 行完整内容）。ATDD 目录**确实有 13 份文件**。之前错误评估已更正。**但 evidence 目录只有 .gitkeep**——这是真实的缺口。

### 5.2 文档可验证性

| 评估项 | 状态 | 详情 |
|--------|------|------|
| ATDD Given-When-Then 覆盖三态 | ✅ | ATDD-M1-AC.md 覆盖正常/边界/异常 |
| exit_criteria 量化 | ❌ | workflow-v2.yaml 全部是 `[false, false, false]` 占位符 |
| 覆盖率阈值量化 | ✅ | coding-standards.mdc L234-239 |
| LLM 成本阈值量化 | ✅ | V3 ¥700/月 |
| interrupt_budget 量化 | ✅ | 5 次/每 run |

### 5.3 文档一致性

| 检查项 | 结果 | 详情 |
|--------|------|------|
| ATDD 与 openapi.yaml 字段对齐 | ⚠️ 未验证 | ATDD-M1-AC.md 引用 `/api/v1/auth/wx-login` 等端点，但未验证 openapi.yaml 中是否真的存在 |
| ATDD 与 TDS 字段对齐 | ⚠️ 未验证 | ATDD 引用 `status='draft'` 等枚举值，未验证 TDS 中是否定义 |
| evidence frontmatter 8 字段 | ✅ | evidence README.md 有完整 schema |
| workflow-v2.yaml 与 DISPATCHER.md 一致性 | ✅ | 16 phase 完全对齐 |
| 6 个新 phase context 文件存在 | ✅ | context/ 目录下有 11-16 共 6 个文件 |

---

## 六、文档依赖关系评估

### 6.1 依赖链路

```
PRD ──┬──→ SRS（docs/requirements/SELFWELL-MVP-SRS.md）✅ 存在
      └──→ SPEC-A0 ──┬──→ TDS ──┬──→ ATDD ✅ 13 份
                      │           │
                      └───────────┴──→ evidence/  ❌ 仅 .gitkeep
```

**关键缺口**：evidence 目录没有真实产物，导致整个文档链路在下游断裂。

### 6.2 版本对齐

| 检查项 | 状态 | 详情 |
|--------|------|------|
| V1.6 → V2 迁移默认值 | ✅ | harness-state.json schema §三有完整迁移逻辑 |
| evidence frontmatter V1.6→V2 扩展 | ✅ | README.md 明确 6→8 字段扩展及默认值 |
| workflow-v2.yaml 与 MIGRATION-V2.md 一致 | ✅ | MIGRATION-V2.md 与 workflow-v2.yaml 完全对齐 |
| ATDD 版本 vs TDS 版本 | ⚠️ 未验证 | ATDD frontmatter 无版本字段 |

---

## 七、文档与代码一致性评估

### 7.1 描述准确性

| 检查项 | 状态 | 详情 |
|--------|------|------|
| ATDD 端点 vs openapi.yaml | ⚠️ 未验证 | ATDD-M1-AC.md 引用 `/api/v1/auth/wx-login`，未验证 openapi.yaml |
| ATDD 枚举值 vs data dictionary | ⚠️ 未验证 | ATDD 引用 `status='draft'`，未验证 data dictionary |
| PR-Gate CI 命令 vs coding-standards | ✅ | pr-gate.yml 引用的命令与 coding-standards.mdc §二完全一致 |
| ad-tdd Phase 3 TDD 循环 vs EXECUTORS.md | ✅ | ad-tdd SKILL.md 与 EXECUTORS.md §2.2 一致 |

### 7.2 路径正确性

| 检查项 | 状态 | 详情 |
|--------|------|------|
| `harness/state/harness-state.json` | ✅ | 存在（9401 字节，完整） |
| `harness/workflow-v2.yaml` | ✅ | 存在（7641 字节，完整） |
| `docs/requirements/SELFWELL-MVP-SRS.md` | ✅ | **存在**（680+ 行） |
| `harness/atdd/` | ✅ | **13 份文件** |
| `harness/evidence/` | ❌ | **仅 .gitkeep，无真实产物** |
| `harness-evidence/SKILL.md` | ❌ | 不存在（但 evidence/README.md 存在，功能覆盖） |
| `harness-review/SKILL.md` | ❌ | 不存在（但 REVIEWERS.md 存在，功能覆盖） |

---

## 八、反馈机制评估（一人模式精简版）

### 8.1 反馈来源

| 来源 | 是否覆盖 | 一人模式评估 |
|------|---------|-------------|
| 测试失败 | ✅ | ✅ verifier 退回 developer |
| Golden Set 回归失败 | ✅ | ✅ PR-Gate 拒绝 |
| 人工 Review | ⚠️ | ⚠️ 一人模式下价值有限（自我评审） |
| CI 失败 | ✅ | ✅ pr-gate.yml 6 项硬卡 |
| 线上故障 | ⚠️ | ⚠️ INCIDENT_RESPONSE phase 未落地 |
| 反馈闭环自动化 | ❌ | ❌ lesson 库为空 |

| 问题 #M4 | 反馈闭环链路未自动化 |
|----------|----------------------|
| **严重程度** | 🟡 **Medium** |
| **发现位置** | `harness-autolearn/SKILL.md`（PR 合入后触发）+ `harness/lessons/` 目录 |
| **类型** | 反馈 |
| **描述** | harness-autolearn 设计了 lesson → pattern → instinct 三级沉淀机制，但 lessons/ 目录为空（没有真实 lesson 文件）。PR 合入后是否真的触发了 autolearn，没有自动化验证。lesson → pattern 的晋升也没有被验证过。一人模式下，踩的坑无法被系统化沉淀，下一个 FR 可能会重复踩同样的坑。 |
| **影响** | 实战中踩的坑无法被系统化沉淀，缺少"自我进化"能力。 |
| **根因** | harness-autolearn 是个协议定义，不是自动化系统。没有 webhook 真正触发它。 |
| **建议** | ① 在 pr-gate.yml 中增加 post-merge hook，触发 autolearn 检查；② 建立 lesson 库（即使只有 1 个）；③ 在 checklist 中增加"lesson 数量 ≥ 1"作为 W12 P2 的验收标准。 |
| **优先级** | **P2** |

---

## 九、调度合理性评估（一人模式核心）

### 9.1 调度触发

| 评估项 | 状态 | 一人模式评估 |
|--------|------|-------------|
| 显式触发（"按 Harness 跑"） | ✅ | ✅ harness-dispatcher SKILL.md §一 |
| 隐式触发（"走流水线"） | ✅ | ✅ 同上 |
| **自动触发** | ❌ | 🔴 **一人模式最需要，但完全缺失** |
| 死锁风险 | ⚠️ | ⚠️ 如果 exit_criteria 永远不满足，会永远卡在当前 phase |

### 9.2 调度策略

| 策略 | 状态 | 一人模式评估 |
|------|------|-------------|
| 串行调度 | ✅ | ⚠️ 必要但需要 `--batch` 模式支持自动续跑 |
| PRE_MORTEM 串行 5 reviewer | ✅ | ⚠️ 对一人模式过于繁琐，需要快速路径 |
| 中断优先级 | ✅ | ✅ interrupt_budget 优先于正常调度 |
| DATA_REPLAY 自动循环 | ✅ | ✅ workflow-v2.yaml 正确：`next: [PRD]` |

| 问题 #C7 | 状态机无自动推进机制 |
|----------|----------------------|
| **严重程度** | 🔴 **Critical** |
| **发现位置** | `harness-dispatcher/SKILL.md` §二 L30-38 + `DISPATCHER.md` §六 |
| **类型** | 调度 |
| **描述** | Dispatcher 的决策完全依赖"人判断当前 phase 已完成 → 说下一步 → Dispatcher 才读 state.json → 决定 next_agent"。没有自动触发机制（没有 cron、没有 webhook、没有事件驱动）。状态机的推进节奏完全受制于人的响应速度。没有 `--auto` flag，没有 `--resume-from` flag，没有批量续跑模式。 |
| **影响** | 一人模式下，用户必须持续说"下一步"才能驱动状态机，机器无法真正"自动跑完全流程"。这与 Harness 的核心价值主张（强制 AI 按步骤走完流水线）相悖。 |
| **根因** | 设计上把 Harness 定义为"人驱动的 review 流水线"而非"机器自动流水线"。没有事件驱动或自动续跑的设计。 |
| **建议** | ① 添加 `--auto` flag：当 exit_criteria 全为 true 时自动推进下一个 phase；② 添加 `--resume-from <phase>` flag：给定一个 state.json，自动识别当前 phase 并续跑；③ 在 GitHub Actions 中支持事件驱动（如 PR 创建 → 自动触发 PRD phase）；④ 实现 `--batch` mode：给定 PRD + SRS，自动跑完全链路。 |
| **优先级** | **P0** |

| 问题 #M5 | 没有 phase 回退机制 |
|----------|--------------------|
| **严重程度** | 🟠 **High** |
| **发现位置** | `harness/README.md` §五场景 C："Harness 不支持回退" |
| **类型** | 调度 |
| **描述** | README.md §五场景 C 明确说"Harness 不支持回退"，标准做法是"写一个新意见留在当前步（不签字），状态文件会保持当前步不推进"。一人模式下，如果 CODE 阶段发现 ARCH_DESIGN 有错误，必须在 CODE 内部 hack 修复，无法退回 ARCH_DESIGN 重新设计。 |
| **影响** | 错误发现的越晚，修复成本越高。 |
| **根因** | 状态机是单向图（无逆向边）。V2 的 interrupt_stack 只追踪中断，不支持退回上一个 phase。 |
| **建议** | ① 至少支持"软回退"（在当前 phase 重做上一个 phase 的工作，但保留当前 phase 已完成的内容）；② 在 interrupt_stack 中增加 `rollback_to` 字段；③ 在 workflow-v2.yaml 中定义"允许回退的 phase 边界"（如 CODE 不允许退回 PRD，但允许退回 ARCH_DESIGN）。 |
| **优先级** | **P1** |

---

## 十、核心场景验证

### 场景：用户已有 PRD 和 SRS，说"继续完成剩余所有步骤"

| 步骤 | 期望行为 | 实际状态 | 一人模式评估 |
|------|---------|---------|-------------|
| 1. Dispatcher 读 state.json | 自动识别当前 phase | state.json 不存在时 dispatcher 初始化 | ⚠️ 需人触发 |
| 2. 自动判断 PRD 是否已完成 | exit_criteria 检查 | 全部是 `[false,false,false]` | 🔴 断点 |
| 3. 自动生成 TDS | tech-architect agent | **没有自动续跑机制** | 🔴 断点 |
| 4. 执行 ATDD | quality-guardian agent | **没有自动续跑机制** | 🔴 断点 |
| 5. 执行 TDD 开发 | developer agent + ad-tdd | **没有自动续跑机制** | 🔴 断点 |
| 6. 执行测试 | verifier agent | **没有自动续跑机制** | 🔴 断点 |
| 7. 提交 commit | developer | **没有自动 commit** | 🔴 断点 |

**结论**：核心场景**完全不可行**。所有断点指向同一个根本问题：**状态机依赖人说"下一步"才能推进，无法自动批量执行**。

---

## 问题清单汇总（一人模式权重重排）

| # | 严重程度 | 类型 | 问题名称 | 优先级 |
|---|----------|------|---------|--------|
| C1 | 🔴 **Critical** | 架构 | exit_criteria 全为占位符，状态机无法判断 phase 完成 | **P0** |
| C2 | 🔴 **Critical** | 架构 | evidence 目录只有 .gitkeep，真实运行产物完全缺失 | **P0** |
| C3 | 🔴 **Critical** | 流程 | 没有一个真实 FR 跑通过全流程 | **P0** |
| C4 | 🔴 **Critical** | 流程 | 状态机无自动推进机制（核心场景不可行） | **P0** |
| C5 | 🟠 **High** | 流程 | ATDD 无法自动转为可执行 pytest 测试 | **P1** |
| C6 | 🟠 **High** | 架构 | check.sh CI 行数校验失效 | **P1** |
| C7 | 🟠 **High** | 调度 | 没有 phase 回退机制 | **P1** |
| M1 | 🟡 **Medium** | 角色 | PRE_MORTEM 5 reviewer 串行对一人模式过于繁琐 | **P2** |
| M2 | 🟡 **Medium** | 角色 | orchestrator 合成在一人模式下增加不必要环节 | **P2** |
| M3 | 🟡 **Medium** | 中断 | LLM 预算超限无明确中断机制 | **P2** |
| M4 | 🟡 **Medium** | 反馈 | 反馈闭环链路未自动化（lesson 库为空） | **P2** |
| M5 | 🟡 **Medium** | 文档 | check.sh 在 Windows 环境无法执行 | **P2** |

---

## 改进路线图

### P0 — 必须修复（阻塞一人模式核心场景）

**1. [C1+C4] 实现 exit_criteria 真实判定 + 状态机自动推进**
- 在 harness-dispatcher SKILL.md 中实现 `exit_criteria` 的自动化检查（用 grep/文件存在性/frontmatter signed）
- 添加 `--auto` flag：当 exit_criteria 全为 true 时自动推进下一个 phase
- 添加 `--resume-from <phase>` flag：给定一个 state.json，自动识别当前 phase 并续跑
- 添加 `--batch` mode：给定 PRD + SRS，自动跑完 PRD→ARCH_DESIGN→...→SIGN_OFF 全链路
- 在 GitHub Actions 中支持事件驱动

**2. [C2+C3] 跑通第一个真实 FR 全流程 + 写 evidence**
- 选 ATDD-M1（微信登录）作为 pilot FR
- 走完 V1.6 全 10 phase（或 V2 全 16 phase）
- 将所有 evidence commit 进仓库作为 baseline
- 复盘所有断点，更新协议

**3. [C7] 实现 phase 回退机制**
- 在 workflow-v2.yaml 中定义"允许回退的 phase 边界"
- 在 state.json 中增加 `rollback_to` 字段
- 实现软回退（在当前 phase 重做上一个 phase 工作）

### P1 — 高优先级（影响效率和正确性）

**4. [C6] 修复 check.sh 行数校验**
- 对 harness-business-interview 设置豁免或上调阈值
- 在 CI 中真正执行 check.sh（扩展 path filter）

**5. [C5] ATDD → pytest 自动转换**
- 引入 pytest-bdd 插件支持 Gherkin
- 或在 ad-tdd SKILL.md 中明确 ATDD → pytest 转换规范
- **立即行动**：至少跑一个 ATDD-M1 scenario 的 pytest 测试

### P2 — 中优先级（优化一人模式体验）

**6. [M1+M2] 一人模式快速路径**
- 在 harness-dispatcher SKILL.md 中增加 `--single-person` flag
- PRE_MORTEM 简化为"requirement-analyst 自审"，保留完整 5 reviewer 作为可选
- orchestrator 合成变为自动摘要

**7. [M3] LLM 预算监控集成**
- 在 state.json 中增加 `llm_cost_yuan` 字段
- 当 llm_cost_yuan > ¥700 时在 CODE/VERIFY 阶段自动触发 AskUser 确认

**8. [M4] 反馈闭环自动化**
- 在 pr-gate.yml 中增加 post-merge autolearn hook
- 建立第一个真实 lesson 文件（即使只有 1 个）

**9. [M5] check.sh 跨平台支持**
- 迁移到 Python（`scripts/check.py`），Python 在 Windows 上天然可跑

---

## 业界最佳实践对比（一人模式视角）

| 维度 | SelfwellAgent Harness | AutoGen | LangGraph | CrewAI | Harness.io |
|------|----------------------|---------|-----------|--------|------------|
| 状态持久化 | JSON 文件 | 内存 | 图结构 | 内存 | PostgreSQL |
| **自动推进** | ❌ | ❌ | ✅（状态机） | ✅ | ✅ |
| 上下文隔离 | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| 回退机制 | ❌ | ❌ | ✅（条件边） | ❌ | ✅ |
| 人工介入 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 性能可观测 | ❌ | ❌ | ✅ | ❌ | ✅ |
| 多角色并行 | ❌ | ⚠️ | ✅ | ✅ | ✅ |
| **一人模式优化** | ❌ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| 实际落地 | 0 FR | 广泛 | 广泛 | 广泛 | 企业级 |

**一人模式最大差距**：AutoGen/CrewAI 的多 Agent 并行和自动推进能力，LangGraph 的状态机图驱动执行，最接近一人模式的"自动化续跑"需求。SelfwellAgent 缺少的核心能力是**状态机的机器自动推进**——这是让"说一句话，机器跑完全流程"成为可能的必要条件。

---

## 结论

**一人模式的核心矛盾**：Harness 设计了一套严谨的多人协作流水线，但一人模式下：

- 5 reviewer 串行变成冗余仪式
- orchestrator 合成变成多余环节
- 每个 phase 间需要人介入变成阻塞点
- 任何手工介入点都在侵蚀自动化的价值

**最高优先级行动**：

1. **立即跑一个最小 FR（如 ATDD-M1）走完 V1.6 全流程**——让 evidence 目录从 .gitkeep 变成有真实产物。这能让所有协议"活起来"。
2. **实现 `--auto` + `--resume-from` 机制**——让状态机真正自动推进，实现"说一句话，机器跑完全流程"。
3. **引入 pytest-bdd 桥接 ATDD 与 pytest**——让 Gherkin 文件可以被自动执行。
4. **为一人模式设计快速路径**——PRE_MORTEM 简化 + orchestrator 变自动摘要。

---

## 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-18 | 初版：基于一人 AI 开发模式视角的全面批判性评估，聚焦单人全链路自动化能力，补全之前评估的遗漏项（SRS/ATDD 实际存在性验证、evidence 真实缺口、一人模式角色效率问题）。 |
