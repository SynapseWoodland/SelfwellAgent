# Harness 改造实施 Checklist（远期：W4 P5 + W12 P3）

> **更新时间**：2026-07-19 23:50
> **拆分时间**：2026-07-19 23:50（架构师拆分：原 checklist.md 727 行 → now 462 + future 263）
> **配套文件**：`harness/checklist-now.md`（in-flight W1 P0 + W4 P1-3）
> **触发条件**：W4 P4（`checklist-now.md` §5）全部完成后启动
> **状态说明**：OK done | doing | pending | blocked

---


## W4 P5 — Harness 评估 V2 缺口修复（High P1：11 项流程/文档缺口）

> **触发**：W4 P4 完成后启动，承接 transcript V2 评估报告 §十一/十二/十三/十四（共 11 项 High P1）。
> **核心原则**：依赖关系决定执行顺序——6.1-6.3（文档）→ 6.4-6.5（流程）→ 6.6（可观测）。每项工时控制在 0.5-1 天。
> **修复顺序**：6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6（Critical P0 闭环后才启动）。

### 6.1 文档陈旧注释清理（D3+D4+D8）

> **架构师判断**：D3/D4/D8 都是 SKILL.md / README.md 中"待 W12 P2 落地"的过期注释——context 已落地但注释未更新，**自我欺骗型问题**。**方案选型**：方案 1（删除过期注释）—— 1 行级最小改动。

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 6.1.1 | **harness-dispatcher/SKILL.md L64-69**：删除所有"待 W12 P2 3.1.x 落地"注释（6 个 phase context 实际已规划在 W4 P4 §5.5 / W12 P2） | `.cursor/skills/harness-dispatcher/SKILL.md` | ⏳ | D3+D8 | — |
| 6.1.2 | **evidence/README.md L39**：删除"W12 P2 落地前暂用 phase-checklist.md" 段落，改为"W12 P2 §3.1.1~3.1.6 完成时按上表命名" | `harness/evidence/README.md` | ⏳ | D4 | — |
| 6.1.3 | **README-V2.md §五 C**：补充明确"阶段回退：暂不支持（架构师判断：一人模式下回退通过 INTERRUPT_REVIEW + 重新 phase 实现）" | `harness/README-V2.md` | ⏳ | Q1 | — |

### 6.2 frontmatter schema 统一（D9+D10+M3）

> **架构师判断**：D9（4 份模板 frontmatter 全不一致）+ D10（lesson 模板与 SKILL 不一致）+ M3（template 用 evidence_id 而非 lesson_id）—— 3 项本质是**同 1 个问题**：v2 8 字段 schema 与 legacy 7 字段 schema 混用。**方案选型**：方案 B（统一为 8 字段，向 evidence/README.md 对齐）—— 最小代价 + 强制统一。

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 6.2.1 | **templates/synthesis.md**：把 6 字段 frontmatter 补齐到 8 字段（加 interrupt_budget + replay_session_id） | `harness/templates/synthesis.md` | ⏳ | D9 | — |
| 6.2.2 | **templates/pre-mortem.md**：把 7 字段（legacy）frontmatter 改为 8 字段（v2） | `harness/templates/pre-mortem.md` | ⏳ | D9 | 5.4.2 |
| 6.2.3 | **templates/acceptance.md**：把 7 字段（legacy）改为 8 字段 | `harness/templates/acceptance.md` | ⏳ | D9 | 5.4.3 |
| 6.2.4 | **templates/lesson-record.md**：把 7 字段（lesson_id 等）改为 5 字段（autolearn SKILL §四真源） | `harness/templates/lesson-record.md` | ⏳ | D10+M3 | — |
| 6.2.5 | **CI 强制**：在 pr-gate-ci.yml（5.1.2 新建）新增 frontmatter schema 校验步骤，evidence/template frontmatter 必须符合 evidence/README.md §一 8 字段定义 | `.github/workflows/pr-gate-ci.yml` | ⏳ | D9+D10 | 5.1.2 |

### 6.3 文档归档/真源关系澄清（D5+Q1+D11）

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 6.3.1 | **README-V2.md 顶部**：加 "本文件是 V2 真源，README.md 已迁移" 声明 | `harness/README-V2.md` | ⏳ | D5+Q1 | — |
| 6.3.2 | **README.md 顶部**：加 DEPRECATED 注释 + 指向 README-V2.md | `harness/README.md` | ⏳ | D5 | — |
| 6.3.3 | **harness/.archive/README.md**：新建（说明归档规则：超过 3 个月未引用的文件归档） | `harness/.archive/README.md` | ⏳ | D5 | — |
| 6.3.4 | **architecture.md / .archive/architecture.md**：2 个都加 DEPRECATED 顶部注释（V3 文档已迁到 V3 架构设计） | 2 个 architecture.md | ⏳ | D5+Q1 | — |
| 6.3.5 | **docs-tureresource-checkList.md**：与 checklist.md 内容对比（重复 / 互补），结果写一份"两份 checklist 关系澄清" 段落 | `harness/checklist.md` §附录 | ⏳ | D11 | docs-tureresource-checkList.md 已删除（D11 通过，关系澄清归入 checklist-now.md） |
| 6.3.6 | **HARNESS-EVALUATION.md 顶部**：加 Tombstone 标签（"已过时，本节为历史快照"），新建 HARNESS-EVALUATION-V2.md 持续更新 | 2 个文件 | ✅ | Q2 | 已删除 HARNESS-EVALUATION.md，归档到 git 历史 |

### 6.4 流程自动化（F1+F2+F3+F5）

> **架构师判断**：F1（一键续跑）+ F2（autolearn webhook）+ F3（replay_session_id 生成器）+ F5（一人 PRE_MORTEM 验证）—— **F1 是单人模式最高 ROI**：把"每 phase 说一句话"变成"一次指令跑完全流程"。**方案选型**：方案 A（CLI 包装）—— 比 GitHub Action 触发更轻量 + 易测试。

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 6.4.1 | **新建 harness/scripts/harness_cli.py**：支持 `--resume-from <phase>` / `--batch <fr_id>` / `--auto --watch state.json` 3 个 flag | `harness/scripts/harness_cli.py` | ⏳ | F1 | 5.5.1 |
| 6.4.2 | **harness/lessons/README.md**：新建（lesson 命名规范 / 分类标准 / 检索入口） | `harness/lessons/README.md` | ⏳ | F2 | — |
| 6.4.3 | **新建 agents/harness/UTILS.md**：定义 `gen_replay_session_id()` 函数 + DATA_REPLAY phase 进入时调用 + 写入 state.json + evidence 12 frontmatter | `agents/harness/UTILS.md` | ⏳ | F3 | — |
| 6.4.4 | **5.3 pilot FR 跑通后**：验证 PRE_MORTEM 一人模式 2 reviewer 真生效（避免理论≠实际） | 1 份 lesson | ⏳ | F5 | 5.3.3 |

### 6.5 中断机制实战验证（E4+S2+S3+M2）

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 6.5.1 | **中断栈持久化测试**：跑 1 个嵌套中断案例（CODE 中断 → INTERRUPT_REVIEW → 中断 → INTERRUPT_REVIEW → 恢复），验证 state.json interrupt_stack LIFO + interrupt_budget 减 1 + resume_from 正确 | 演练记录 + lesson | ⏳ | E4 | 5.3.7 |
| 6.5.2 | **workflow-v2.yaml interrupt 字段扩展**：加 `interrupt_priority` (USER/orchestrator/system) + `interrupt_freeze_evidence: true` + `interrupt_serializer` 字段 | `harness/workflow-v2.yaml` | ⏳ | S2 | — |
| 6.5.3 | **harness-state.schema.md**：加 `interrupt_consumed_stack` 字段；DISPATCHER.md 加 INTERRUPT_REVIEW 决策路由表（continue/defer/escalate） | 2 个文件 | ⏳ | S3+M2 | — |

### 6.6 harness-evidence / harness-review SKILL 缺失补救（D6）—— ✅ 已完成

> **架构师判断**：D6（V2 评估多次引用不存在的 `harness-evidence/SKILL.md` / `harness-review/SKILL.md`）—— **方案选型**：方案 C（明确声明已被 harness-dispatcher + REVIEWERS.md / evidence/README.md 整合）—— 不新建 SKILL（避免 SKILL 膨胀），删除 V2 评估中的过期引用。V2 评估文件已删除归档。

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 6.6.1 | **V2 评估**：grep 替换所有 `harness-evidence/SKILL.md` / `harness-review/SKILL.md` → `evidence/README.md` / `agents/harness/REVIEWERS.md`，顶部加 §一 "SKILL 整合声明" | HARNESS-EVALUATION.md 已删除 | ✅ | D6 | — |

### 6.7 High P1 验收

- [ ] 6.1.x：grep 整个 harness/ 无"待...落地"过期注释
- [ ] 6.2.x：4 份 template frontmatter 全部符合 8 字段 schema，CI 校验通过
- [ ] 6.3.x：README.md / README-V2.md 关系明确，.archive/README.md 存在
- [ ] 6.4.1：CLI `--batch FR-PILOT-ATDD-M1` 真自动跑通 16 phase
- [ ] 6.5.1：嵌套中断案例演练通过

### 6.8 High P1 阶段完成度

```
░░░░░░░░░░░░░░░░░░░░  0%   ⏳ 0/19 任务完成
                       预计工时：4-5 天（启动条件：W4 P4 §5.7 全部完成）
```

---

## W12 P3 — Harness 评估 V2 缺口修复（Medium P2 + Low P3：13 项远期缺口）

> **触发**：transcript V2 评估报告 §十三/十四（共 11 项 Medium P2 + 2 项 Low P3）。
> **核心原则**：远期优化，**仅在 W4 P4 + W4 P5 全部闭环后才启动**。一人 AI 模式下 ROI 较低（更多为多团队协作场景设计）。
> **修复顺序**：7.1 → 7.2 → 7.3 → 7.4（按 ROI 排序：metrics → 回滚 → FR↔ADR → observability）。

### 7.1 Harness metrics 输出（F4+F8）

> **架构师判断**：F4（metrics 字段）+ F8（observability）本质是同 1 个能力。**方案选型**：方案 A（state.json 加 metrics 字段 + 新建 METRICS.md 速查表）—— 1 天可落地；不做 Grafana 看板（投资回报低，多人协作场景才需要）。

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 7.1.1 | **harness-state.schema.md**：扩展 schema 加 `metrics` 字段（`{llm_cost_yuan, total_tokens, total_duration_s, retry_count, interrupt_count}`） | `harness/state/harness-state.schema.md` | ⏳ | F4 | — |
| 7.1.2 | **evidence template frontmatter**：加 `phase_duration_s` 字段 | 4 份 templates | ⏳ | F4 | 6.2.x |
| 7.1.3 | **新建 harness/METRICS.md 速查表**：每 run 报告 4 个关键指标（LLM cost / 总耗时 / retry 数 / interrupt 数），对齐 DORA Metrics | `harness/METRICS.md` | ⏳ | F4+F8 | 7.1.1 |

### 7.2 phase 回退机制（F-追加 + HARNESS-EVALUATION M5）

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 7.2.1 | **harness-state.schema.md**：加 `rollback_to` 字段 + `rollback_reason` 字段（值可为 ARCH_CHANGE / REQUIREMENT_CHANGE / PRODUCTION_INCIDENT） | `harness/state/harness-state.schema.md` | ⏳ | M5 | — |
| 7.2.2 | **DISPATCHER.md**：加"phase rollback 协议"章节——回退到指定 phase + 重新生成 evidence + state.json `rollback_history` 字段追加 | `agents/harness/DISPATCHER.md` | ⏳ | M5 | 7.2.1 |
| 7.2.3 | **5.3.7 rollback 演练复用**：把 INTERRUPT_REVIEW + rollback 路径纳入 harness_cli.py（6.4.1） | `harness/scripts/harness_cli.py` | ⏳ | M5+F1 | 5.3.7 + 6.4.1 |

### 7.3 FR ↔ ADR ↔ TDS 反向链接校验（D-追加）

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 7.3.1 | **新建 harness/scripts/check_links.py**：扫 `docs/fr/*/FR-*.md` + `docs/architecture/adr/*/ADR-*.md` + `docs/spec/TDS-*.md`，检查 fr_id ↔ adr_refs ↔ tds_ref 三向引用无悬空 | `harness/scripts/check_links.py` | ⏳ | D-追加 | — |
| 7.3.2 | **pr-gate-ci.yml（5.1.2 新建）**：新增卡口 8 调用 check_links.py --strict | `.github/workflows/pr-gate-ci.yml` | ⏳ | D-追加 | 5.1.2 + 7.3.1 |

### 7.4 80% 残留阈值清理（F9）

> **架构师判断**：F9（多个文档残留"≥ 80%" 阈值）—— L0-L6 审计 §三已识别 2 处，但 pr-gate SKILL.md 还有 1 处未清。**完全清理**而非"留个别例外"。

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 7.4.1 | **pr-gate/SKILL.md L25-30**：`--cov-fail-under=80` → 60；同步加注释指向 `l0-l6-gates.mdc` §二 | `.cursor/skills/pr-gate/SKILL.md` 或 `pr-gate-human/SKILL.md`（5.1.3 改名后） | ⏳ | F9 | 5.1.3 |
| 7.4.2 | **grep 残留**：全仓 grep `>= 80%` / `≥ 80%` / `--cov-fail-under=80`，全部改为指向 `l0-l6-gates.mdc` §二 | 多文件 | ⏳ | F9 | — |

### 7.5 snapshot 子目录创建（M4）

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 7.5.1 | **harness/state/snapshots/**：新建子目录（含 .gitkeep + README.md 说明快照规则） | `harness/state/snapshots/` | ⏳ | M4 | — |
| 7.5.2 | **SNAPSHOT-INSTRUCTIONS.md**：去除"计划中"措辞，改为"快照生成器已就绪（scripts/harness_cli.py --snapshot <phase>）" | `harness/state/SNAPSHOT-INSTRUCTIONS.md` | ⏳ | M4 | 7.5.1 + 6.4.1 |

### 7.6 checklist 自我膨胀治理（Q3）

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 7.6.1 | **拆分 checklist**：git mv `harness/checklist.md` → `harness/checklist-W1-W4.md`；新建 `checklist-W12.md` | 2 个 checklist | ⏳ | Q3 | — |
| 7.6.2 | **harness/CHECKLIST-INDEX.md**：新建索引页（指向 4 个分册 + 总览图） | `harness/CHECKLIST-INDEX.md` | ⏳ | Q3 | 7.6.1 |

### 7.7 lessons README + lesson 库补齐（M1）

| # | 任务 | 产出 | 状态 | 来源 | 依赖 |
|---|------|------|:---:|------|------|
| 7.7.1 | **harness/lessons/README.md**：命名规范 + 触发场景 + 检索入口 + 晋升路径（lesson → pattern → instinct） | `harness/lessons/README.md` | ⏳ | M1 | 6.4.2（前置） |

> 注：M1 与 6.4.2 重复——以 6.4.2 为准，7.7.1 不再单独执行。

### 7.8 Medium P2 + Low P3 验收

- [ ] 7.1.x：跑 1 个 pilot run 后 state.json 含完整 metrics 字段
- [ ] 7.2.x：rollback_to 字段写入 + 演练恢复成功
- [ ] 7.3.x：故意改 FR 去掉 ADR 引用，CI 拒绝
- [ ] 7.4.x：grep `>= 80%` 全仓 0 命中（除 l0-l6-gates.mdc 真源定义）
- [ ] 7.5.x：snapshot 子目录真实存在 + `python harness_cli.py --snapshot` 可调用
- [ ] 7.6.x：checklist 拆分完成 + 总览索引可读

### 7.9 Medium P2 + Low P3 阶段完成度

```
░░░░░░░░░░░░░░░░░░░░  0%   ⏳ 0/13 任务完成（实际去重后 11 项）
                       预计工时：4-5 天（启动条件：W4 P4 + W4 P5 全部完成）
```

---

---

## 总览图（更新后，2026-07-19 架构师复核）

```
W1 P0      W4 P1+P2+P3+P4+P5        W12 P2          W12 P3
[████]    [████████████████████]    [░░░░░░░░░░]    [░░░░░░░░░░]
 100%       P1:73%(⚠️回滚后)         0%               0%
            P2:17%
            P3:100% ✅
            P4:0% ⚠️新增
            P5:0% ⚠️新增
 ✅18        ✅7 ⏳4                 ⏳13            ⏳13（去重后 11）
            + P2:✅2 ⏳10
            + P3:✅21
            + P4:⏳24 ⚠️新增
            + P5:⏳19 ⚠️新增
```

| 阶段 | 完成 | 进行中 | 待启动 | 总计 | 备注 |
|------|------|--------|--------|------|------|
| **W1 P0** | ✅ 18 | — | — | 18 | — |
| **W4 P1** | ✅ 7 ⚠️ | ⏳ 4 | — | 11 | §2.1.4 / §2.1.5 / §4.5.12d 已回滚 |
| **W4 P2** | ✅ 2 | ⏳ 0 | ⏳ 10 | 12 | — |
| **W4 P3** | ✅ 21 | — | — | 21 | L0-L6 一致性 + 双轨制 |
| **W4 P4** ⚠️新增 | ✅ 9 | — | ⏳ 15 | 24 | Critical P0 修复（X1/X2/D1/D2/S1 全部完成 = 9/24 = 37.5%） |
| **W4 P5** ⚠️新增 | — | — | ⏳ 19 | 19 | High P1 修复（D3~D11/F1~F5/E2~E4） |
| **W12 P2** | — | — | ⏳ 13 | 13 | 6 个新 phase 落地（依赖 W4 P4 §5.5） |
| **W12 P3** ⚠️新增 | — | — | ⏳ 11 | 11 | Medium P2 + Low P3 远期缺口 |
| **合计** | **57** ⚠️ | **4** | **68** ⚠️ | **129** ⚠️ | 较 V3 增加 54 项（架构师复核重置进度），本轮完成 9 项 |

> **架构师复核警示**：原 "✅48 / ⏳23 / 总计 75" 已不准确——3 处假完成已回滚（W4 P1 §2.1.4 / §2.1.5 / §4.5.12d），新增 3 个阶段 54 项（W4 P4 + W4 P5 + W12 P3）。所有"✅" 状态需要在下一轮 review 时逐项验证。

---

## 下一步行动（架构师优先级，2026-07-19）

| 优先级 | 行动 | 谁来做 | 状态 |
|--------|------|--------|------|
| 🔴 **P0 #1** | **5.1.1-5.1.4 pr-gate.yml 真实化**：拆 markdown + 新建真 pr-gate-ci.yml + 拆 SKILL + 本地等价验证 PASS | 我做，你 review | ✅ |
| 🔴 **P0 #2** | **5.2.1-5.2.3 state.json 实战化**：重命名 + 新建真实 run + 1 份占位 evidence | 我做 | ⏳ |
| 🔴 **P0 #3** | **5.4.1-5.4.4 文档引用修复**：DISPATCHER L63 / templates L150 L99 / workflow.yaml DEPRECATED | 我做 | ✅ |
| 🔴 **P0 #4** | **5.5.1-5.5.3 跨平台 exit_criteria**：写 check_phase.py + CI 集成 | 我做 | ✅ |
| 🔴 **P0 #5** | **5.6.1 harness-ci.yml path filter 扩展** | 我做 | ⏳ |
| 🟡 **P1 #1** | **5.3.1-5.3.7 跑 pilot FR**（ATDD-M1 微信登录）走完 16 phase + 8 份 evidence + 1 份 lesson + 回滚演练 | 你在场边看 | ⏳ |
| 🟡 **P1 #2** | **6.1-6.6 High P1 修复**（依赖 W4 P4 全部闭环） | 我做，你 review | ⏳ |
| 🟢 **P2** | **7.1-7.7 Medium P2 + Low P3**（依赖 W4 P4 + W4 P5 全部闭环） | 我做 | ⏳ |
| 🟢 **长期** | **W12 P2 §3.1.1~3.1.6** 6 个新 phase 落地（依赖 5.5 6 份 context 模板补齐） | 下一步 | ⏳ |

---

> **最后更新**：2026-07-19 23:10（架构师实施第二轮：P0 #3 + P0 #4 全部完成）
> **本次变更（22:55 → 23:10）**：
> - ✅ 5.4.1-5.4.4 全部完成：DISPATCHER.md L63 + pre-mortem.md L150 + acceptance.md L99 + workflow.yaml DEPRECATED 头（含 YAML 合法性验证 10 phase）
> - ✅ 5.5.1-5.5.3 全部完成：check_phase.py 349 行跨平台（_builtin_test / _builtin_grep 解决 Windows 找不到 test/grep）+ DISPATCHER.md §三.b 集成 CLI 用法 + Gate 8 软警告 + harness-ci 矩阵 ubuntu+windows
> - ✅ §2.1.4 二次校正：误判已恢复（harness/context/ 实有 7 文件）
> - 新增文件：`harness/scripts/check_phase.py` / `.github/workflows/harness-ci.yml` 加 job
> - 修改文件：`agents/harness/DISPATCHER.md`（+32/-15）/ `harness/templates/{pre-mortem,acceptance}.md`（-2 +2）/ `harness/workflow.yaml`（+30 行 DEPRECATED 头）
> - **端到端验证**：PowerShell 上跑 check_phase.py 6/6 ALL PASS（--list / --json / PRD FAIL / --all / NONEXISTENT / builtin test+grep）
> **下次更新**：5.2.x（state.json 实战化）完成后
> **参考**：
> - transcript `c3b2edcc-5117-416d-990e-ed76f53d1e7b`（V2 评估报告 V1 + V2，共 32 项缺口，已整合到 checklist + 附录 A）
> - V2 评估报告已删除归档（git 历史保留）
> - `harness/L0-L6-AUDIT-2026-07-19.md`（L0-L6 一致性审计）
> - `.github/workflows/pr-gate-ci.yml`（真 workflow，9 卡口 = 7 硬 + 1 软警告 + 1 总闸）
> - `harness/scripts/check_phase.py`（349 行跨平台 exit_criteria 判定）

---

## 附录 A：架构师方案选型决策记录（透明化所有拒绝方案）

> **目的**：让所有"为什么是 X 不是 Y"的判断可追溯，避免下次有人质疑时重复讨论。

| 缺口 | 推荐方案 | 否决方案 | 否决理由 |
|------|----------|----------|----------|
| X1 (pr-gate.yml) | **方案 B** 改名 .md + 新建真 pr-gate-ci.yml（0.5 天） | A 彻底改造 / C 维持现状 | A 工作量过大（2-3 天）+ 改动太集中风险高；C 在 1 人 AI 模式下不可持续 |
| X2 (pr-gate SKILL) | 拆为 pr-gate-human + pr-gate-ci | 维持现状 | 与 X1 修复配套；否则即使真 workflow 上线，SKILL 描述与实现仍错配 |
| X3 (state.json 仍初始化) | 单次手动更新 + 1 份占位 evidence | 等跑完整 pilot FR | X3 不需要等完整 FR——单独修复即可关闭缺口 |
| D1/D2 (文档引用错) | 改引用为 phase-checklist.md（最小改动） | 补齐 6 份缺失 phase context | 补齐需 4-6 小时，且 W4 P4 §5.5 后续会重建 context |
| S1 (跨平台 exit_criteria) | 写 check_phase.py（DISPATCHER 已规划） | 改 exit_criteria 为 Python 函数 | 破坏 YAML 结构 + 16 phase 全部重写；DISPATCHER.md §三.b 已规划方案 A |
| F4/F8 (metrics + observability) | state.json metrics 字段 + METRICS.md | Grafana 看板 | 1 人 AI 模式无 Grafana 维护能力；METRICS.md 速查表已够 |
| F-追加 (回退机制) | rollback_to + rollback_reason 字段 + INTERRUPT_REVIEW 路径复用 | 全新 phase rollback 系统 | 复用 INTERRUPT_REVIEW 路径成本最低，1 天可落地 |
| D-追加 (FR↔ADR↔TDS 校验) | 新建 check_links.py + pr-gate-ci.yml 卡口 8 | 全文反向链接工具 | 1 人 AI 模式写完整工具 ROI 低；CI 卡口方案已够 |
| Q3 (checklist 自我膨胀) | 拆为 checklist-W1-W4.md + checklist-W12.md | 维持单文件 | 当前 387 行已超易读阈值；拆分后各 ≤ 200 行 |
| M3 (lesson 模板字段不一致) | 统一为 5 字段向 autolearn SKILL 对齐 | 7 字段向前 | 实战 lesson 文件已是 5 字段；向实战对齐零迁移成本 |
| E1 (跑 pilot FR) | ATDD-M1 微信登录（复杂度最低 + 已有 ATDD-AC） | ATDD-M2 ~ M14 | M1 是最小可跑通单元；其他 FR 等 E1 跑通再复用框架 |

---

## 附录 B：架构师"不修"清单（明确剔除项）

> **目的**：避免每次评估都重复讨论已被否决的方案。

| 缺口 | 不修原因 |
|------|----------|
| M3 (LLM 预算监控中断机制) | 当前 ¥700/月预算足够，无监控紧迫性（已记 §4.4） |
| LLM Cost 实时熔断 | 一人模式下手动控制 LLM 调用节奏已足够，无需自动化熔断 |
| 5 reviewer 串行（PRE_MORTEM） | 一人模式 `one_person_synthesis: true` 已跳过，无需降级 |
| D-追加（V3 架构图谱） | mermaid 已能覆盖 80% 场景；纯文本架构图谱 ROI 低 |
| 多语言 i18n（中英） | 当前阶段中文优先，i18n 在 M3 之后 |
| cursor-cloud-agent 集成 | 1 人 AI 模式不适用 Cloud Agent |
