# Harness Engineering 现状 vs 参考架构 Gap 分析

> **本文档目的**：把参考架构图（4 层 × 11 步 + 驱动/记忆/进化三件套）逐项拆解，对照当前 Harness 体系的 30+ 个文件，列出"已落地 / 部分落地 / 完全缺失"3 档结论。
> **基线图**：用户提供版（参见文档首段引用）
> **基线日期**：2026-07-17
> **对照范围**：`harness/` + `agents/harness/` + `.cursor/skills/harness-*/` 共 35 个文件

---

## 0. 速查结论

| 层级 | 落地率 | 关键缺口 |
|------|-------|---------|
| **L1 流程层（11 步）** | **4/11 完全落地，7/11 缺失** | 缺数据回流 / 故障管理 / 持续运营 / 客户反馈收集 |
| **L2 驱动层（4 件套）** | **1.5/4 落地** | 缺业务经验沉淀机制落地、SDD 协议未串接、Reviewers 仅协议未跑通 |
| **L3 记忆层（用户反馈 / 数据回流）** | **0/2** | 完全缺失 |
| **L4 进化层（平台 + 工具双螺旋）** | **0/2** | 完全缺失，仅有 lessons 目录空壳 |

**总体评分**：**协议文档层 90 分，落地执行层 15 分**。

---

## 1. 图与现状对照（逐项）

### 1.1 L1 流程层（11 步）— 当前只覆盖 4 步

| # | 图中节点 | 当前是否覆盖 | 覆盖证据 | Gap |
|---|---------|------------|---------|-----|
| 1 | **客户需求** | ⚠️ 部分 | `workflow.yaml` 第 4 行 `PRD` 阶段 + `01-requirement.md` evidence + ATDD 文件夹已有 13 份（M1~M14） | 缺**客户反馈收集的反馈源**（图示输入箭头指向外部客户） |
| 2 | **需求设计** | ✅ 覆盖 | PRD phase + `prd-phase.md` context + `01-requirement.md` 模板 | 无 |
| 3 | **架构设计** | ✅ 覆盖 | `ARCH_DESIGN` + `ad-phase.md` + TDS 文件 13 份 | 无 |
| 4 | **研发实现** | ⚠️ 部分 | `CODE` phase + `developer` 角色 + `ad-tdd` Phase 3 RED-GREEN-REFACTOR | 缺**实际跑通**案例（无任何 FR 走完 Harness 全流程的 record） |
| 5 | **静态质检** | ⚠️ 部分 | `VERIFY` + `verifier` + L0-L4 命令定义 | 缺 lint/mypy 集成到 CI（`.github/workflows/` 未串入 harness grep 兜底） |
| 6 | **测试验证** | ⚠️ 部分 | `VERIFY` + 测试员 + ATDD 用例 | ATDD 验证脚本未实际跑过（pytest 集成未串通） |
| 7 | **安全测试** | 🔴 **完全缺失** | `03b-security.md` evidence 模板有，但**无安全测试阶段** | 流程图第 7 步 "安全测试" 在 `workflow.yaml` 无独立 phase；当前安全评审只作为 Pre-Mortem 的一部分 |
| 8 | **部署上线** | ⚠️ 部分 | `DEPLOY` + `deployer` + `evidence/06-deploy.md` | 缺实际部署脚本（`docker-compose` / `alembic` 集成未实操） |
| 9 | **数据回流** | 🔴 **完全缺失** | 无 | **缺一个完整的数据回流子系统**：埋点 + 上报 + 入库 + 监控告警 |
| 10 | **故障管理** | 🔴 **完全缺失** | 无 | 缺故障响应流程 / runbook / oncall 规则 / 复盘模板 |
| 11 | **持续运营** | 🔴 **完全缺失** | 无 | 缺运营指标监控 / 用户反馈→产品迭代闭环 / AB 测试 / 灰度发布 |

**L1 缺口小结**：当前 Harness 的"流程"实际上是**只到上线为止**（1→8），上线的"数据回流-故障-运营"三个阶段完全没设计。

---

### 1.2 L2 驱动层（4 件套）— 只覆盖一半

| 驱动件 | 图位置 | 当前是否覆盖 | 覆盖证据 | Gap |
|--------|--------|------------|---------|-----|
| **业务经验沉淀** | 流程层右侧 | 🔴 缺失 | 仅 `harness/lessons/README.md` 和 `lesson-record.md` 模板，**0 个真实 lesson 文件** | 缺（1）lesson 触发的强制点（哪步必须问"是否沉淀"）；（2）pattern → coding-standards/PATTERNS.md 写入流程实操；（3）instinct → RULES.md 写入流程实操 |
| **SDD 协议** | 流程层右侧 | ⚠️ 部分 | 有 `ad-tdd/SKILL.md` Phase 1-3 + `ad-tdd/TDS-TEMPLATE.md`，但 | 缺（1）`docs/SPEC/` 目录下的完整 SPEC 索引（现有仅 SPEC-A0-MASTER-IA + 6 份 M*）；（2）SDD → TDD 的**强制转换点**（当前是建议而非强制）；（3）Skill 与 Harness workflow 的串接验证（`ad-tdd/SKILL.md` 是独立 Skill，未被 Harness 强制调用） |
| **Skills 协议** | 流程层右侧 | ⚠️ 部分 | 4 个 Harness Skill（dispatcher/evidence/review/autolearn）+ 6 个基础 Skill（coding-standards/golden-set/ad-tdd/pr-gate/frontend-standards/sdd-tdd） | 缺（1）Skill 间的依赖图文档化；（2）Skill 加载顺序约定（哪些 alwaysApply，哪些按需）；（3）Skill 升级时的兼容性测试机制 |
| **Reviewers** | 流程层右侧 | ⚠️ 部分 | `agents/harness/REVIEWERS.md` 定义 5 个评审角色（3 核心 + 2 扩展），`harness-review/SKILL.md` 编排 | 缺（1）**实际跑过一次**的 Pre-Mortem 案例；（2）**对抗辩论** `adversarial-debate.md` 模板存在但无实战案例；（3）5 角色的真正调用顺序 / 并行 vs 串行（SKILL.md 写"串行"但实际 Claude 主会话上下文是否能扛住 5 轮未验证） |

**L2 缺口小结**：4 件套的**协议定义齐全**，但**实际触发 / 跑通 / 串接验证**全部缺失。

---

### 1.3 L3 记忆层（用户反馈 + 数据回流）— 完全缺失

| 记忆类型 | 图位置 | 当前是否覆盖 | 覆盖证据 | Gap |
|---------|--------|------------|---------|-----|
| **用户反馈** | 图左侧反馈入口 | 🔴 缺失 | 无 | 缺（1）`apps/` 前端埋点 SDK；（2）反馈事件 schema（`feedback_events` 表）；（3）反馈→FR 编号→lesson 的回流链路 |
| **数据回流** | 图底部数据入口 | 🔴 缺失 | 无 | 缺（1）后端埋点中间件；（2）`PostgreSQL` 事件表 schema；（3）埋点数据接入 Eval Runner 做 baseline 对比 |

**L3 缺口小结**：**记忆层是 0**。当前 Harness 体系对"用户说了啥 / 用了啥 / 出错了啥"完全无感，等于 AI 写完代码上线后**没有触觉**。

---

### 1.4 L4 进化层（平台 + 工具双螺旋）— 完全缺失

| 进化机制 | 图位置 | 当前是否覆盖 | 覆盖证据 | Gap |
|---------|--------|------------|---------|-----|
| **平台进化** | 图右侧上升箭头 | 🔴 缺失 | 无 | 缺（1）`harness-autolearn` Skill 实际触发机制（仅协议，未跑通）；（2）lessons → pattern 升级的人工触发点；（3）平台版本号管理 + 向后兼容策略 |
| **工具进化** | 图左侧上升箭头 | 🔴 缺失 | 无 | 缺（1）工具自身（ruff/mypy/pytest/Golden Set）的升级检测；（2）工具升级后 Harness 的兼容性回归测试；（3）工具 bug 反馈通道 |

**L4 缺口小结**：进化层是 0。Harness 自身不会"自我迭代"——所有 lessons 目录是空壳，没有真实跑过 PR 合入后的沉淀流程。

---

## 2. 协议层 vs 执行层对照

虽然协议层（`agents/harness/*.md` + `.cursor/skills/harness-*/SKILL.md` + `harness/templates/*`）**写得相当扎实**（R-2 标注、grep 兜底、退出条件、角色权限矩阵全有），但执行层**几乎是零**：

| 维度 | 协议层状态 | 执行层状态 |
|------|----------|----------|
| **有文档** | 35 个文件齐全 ✅ | 0 个真实 run 记录 ❌ |
| **有自动化** | grep 兜底命令已写 ✅ | grep 命令未接到 CI ❌ |
| **有案例** | ATDD 模板 13 份 + 3 模板 ✅ | 真实跑通案例 0 ❌ |
| **有数据** | workflow.yaml + state.example ✅ | 真实 harness-state.json 0 ❌ |

**结论**：项目处于**"协议齐备但从未落地"**状态。

---

## 3. 优先级排序 + 工时估算

按"业务价值 × 可落地难度"两维评估，给出 4 档优先级：

### P0 — 必须马上做（阻塞 Harness 真运行）

| Gap | 工时 | 说明 |
|-----|------|------|
| **真实跑 1 个 FR 走完全流程** | 2-3 天 | 选 1 个小 FR（如某条 ATDD-M*-AC）走完 1→8 全流程，跑通 state.json + 8 个 evidence + 真实 PR |
| **把 grep 兜底接入 CI** | 0.5 天 | 在 `.github/workflows/backend-ci.yml` 加 4 条 grep 命令，对应 `harness-evidence/SKILL.md` §十 |
| **写真实 harness-state.json** | 0.5 天 | 替换 `harness-state.example.json` 为真实 run 的 state |
| **修 ATDD 流程自动化** | 1 天 | 把 ATDD Gherkin 用例接入 pytest，让 verifier 阶段能自动跑 |

**P0 总工时**：4-5 天

---

### P1 — 2 周内补齐（让 Harness 覆盖完整开发循环）

| Gap | 工时 | 说明 |
|-----|------|------|
| **补"安全测试"独立 phase** | 1 天 | 在 `workflow.yaml` 加 `SECURITY_TEST` 阶段（第 7 步），单独跑 bandit + 安全评审 |
| **补"数据回流"埋点中间件** | 3 天 | 后端 `core/telemetry/` 埋点 + PostgreSQL 事件表 + 前端 SDK |
| **补 Lesson 触发机制** | 1 天 | 在 SIGN_OFF 阶段末尾硬性调用 harness-autolearn，问"是否沉淀" |
| **补 Lesson → Pattern 实战** | 1 天 | 跑 1-2 个真实 lesson 案例，验证 → PATTERNS.md 写入流程 |

**P1 总工时**：6 天

---

### P2 — 1 个月内补齐（让 Harness 真有"运营"能力）

| Gap | 工时 | 说明 |
|-----|------|------|
| **补"故障管理"流程** | 3 天 | runbook 模板 + oncall 排班 + 故障复盘模板（`docs/runbook/`） |
| **补"持续运营"指标监控** | 3 天 | Prometheus 指标 + Grafana dashboard + 用户活跃度→产品迭代回路 |
| **补"客户反馈"采集** | 2 天 | 前端反馈按钮 + 反馈事件入 PostgreSQL + 反馈→FR 编号映射 |
| **补"平台进化"自动触发** | 1 天 | PR 合入 webhook → 触发 harness-autolearn 自动评估 |

**P2 总工时**：9 天

---

### P3 — 长期演进（双螺旋自我迭代）

| Gap | 工时 | 说明 |
|-----|------|------|
| **Skill 升级兼容性测试** | 3 天 | Skill 版本变更时自动跑回归 |
| **工具升级检测机制** | 2 天 | ruff/mypy/pytest 升级时检测 Harness 兼容性 |
| **完整跑通 5 个 FR 走 Harness** | 10 天 | 选 5 个不同类型 FR（小型/中型/大型/前端/后端），覆盖所有 phase 变体 |

**P3 总工时**：15 天

---

## 4. 当前能用的部分（不用等补全）

虽然有 7/11 流程缺失，但下面这些**今天就能用**：

```
✅ 可以跑流程：PRD → ARCH_DESIGN → PRE_MORTEM → ATDD → PLAN → CODE → VERIFY → DEPLOY → REGRESSION → SIGN_OFF
✅ 可以让 5 角色评审：requirement / tech / quality / security / devops
✅ 可以写 evidence 链：state.json + 8 份 evidence + frontmatter
✅ 可以触发自动晋升：lesson → pattern → instinct 三级机制
✅ 可以挡 R-2 红线：grep if.*score.*> agents/harness/ 必须无命中
```

**唯一缺的不是协议，是真实 run**。补一个 FR 走完全流程，就能让所有协议"活起来"。

---

## 5. 与参考图的最大差异（一句话版）

参考图强调的是 **"上线不是结束，运营才是开始"** 的完整工程闭环。

当前 Harness 只做到了 **"上线就结束"**——从需求到部署是齐的，但从部署回流到需求这一段（数据 + 反馈 + 故障 + 进化）完全是空白。

如果只能做一件事，**优先做"补一个真实 FR 走完全流程 + 接入 CI grep"**——这能让现有 35 个协议文件从"纸面"变成"可验证"，其他 Gap 可以逐步补。

---

## 6. 验收清单（做完后逐项打勾）

### P0 验收（4-5 天内完成）

- [ ] 至少 1 个 FR 的 `harness-state.json` 是真实 run（非 example）
- [ ] 同一 FR 的 8 个 evidence 文件全部存在且 frontmatter 7 字段齐全
- [ ] `.github/workflows/backend-ci.yml` 包含 4 条 grep 兜底命令
- [ ] CI 跑通任意 FR 后自动报告"harness evidence 完整性"✅ / ❌
- [ ] ATDD 至少 1 个用例 pytest 跑通

### P1 验收（2 周内完成）

- [ ] `workflow.yaml` 第 7 步 "SECURITY_TEST" 独立 phase
- [ ] 后端埋点中间件 + PostgreSQL 事件表 + 至少 3 类事件上报
- [ ] 至少 1 个真实 lesson 文件 + 1 个真实 PATTERN.md
- [ ] harness-autolearn 在 SIGN_OFF 末尾自动触发

### P2 验收（1 个月内完成）

- [ ] `docs/runbook/` 至少 3 个 runbook 模板
- [ ] Prometheus 至少 5 个业务指标 + 1 个 Grafana dashboard
- [ ] 前端反馈按钮 + 反馈入 PostgreSQL + 反馈→FR 映射链路
- [ ] PR 合入 webhook → autolearn 自动评估链路

### P3 验收（长期）

- [ ] Skill 升级时自动跑兼容性回归
- [ ] 工具升级检测机制
- [ ] 5 个不同类型 FR 走完 Harness 全流程

---

## 7. 参考文档

- 参考图：用户提供的"Harness Engineering 4 层架构图"
- 现有协议真源：`agents/harness/DISPATCHER.md` / `ORCHESTRATOR.md` / `REVIEWERS.md` / `EXECUTORS.md`
- 现有 Skill 真源：`.cursor/skills/harness-dispatcher/` / `harness-evidence/` / `harness-review/` / `harness-autolearn/`
- 状态机：`harness/workflow.yaml`
- V3 主架构：`docs/architecture/tech-architecture-design-v3.md`
- 现状入口：`harness/README.md`

---

## 8. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-17 | 初版：按用户提供的 4 层架构图（流程 11 步 + 驱动 4 件套 + 记忆 2 件 + 进化 2 件）逐项对照 35 个现状文件，输出 4 档优先级 + 验收清单 |
