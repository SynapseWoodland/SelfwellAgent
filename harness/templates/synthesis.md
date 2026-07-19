---
phase: <PRE_MORTEM | SIGN_OFF>
run_id: <uuid>                              # 与 harness-state.json 的 run_id 一致
role: orchestrator                          # A 档：唯一允许写本文件的角色（原 reviewer_role + author_agent 合并）
fr_refs: [<FR-XXX-XX>, ...]                 # 至少 1 个；PRE_MORTEM / SIGN_OFF 必填
adr_refs: [<ADR-XXXX>, ...]                 # 涉及技术选型时必填；无则填 []（A 档保留审计锚点）
synthesis_inputs:                           # 合成输入的 evidence 文件相对路径列表（相对 harness/evidence/）
  - 01-requirement.md
  - 02-tech-design.md
  - 03-quality.md
  - 03b-security.md
  - 03c-devops.md
tds_ref: <docs/spec/TDS-<id>.md>            # 上游基线，用于核对 reviewer 是否与 TDS 一致
signed: true                                # PRE_MORTEM / SIGN_OFF 必填 true
---

# 合成模板（含 2 个内嵌示例）

> 合成时间：YYYY-MM-DD HH:MM；合成协议：[`agents/harness/ORCHESTRATOR.md`](../../../agents/harness/ORCHESTRATOR.md) §三
> frontmatter 6 字段：`phase / run_id / role / fr_refs / adr_refs / signed`（A 档精简）
> 状态：当且仅当下方三段均填写完毕、`signed: true`，dispatcher 才允许路由到下一阶段

---

## 〇、合成前置自检（必填，未通过则拒绝进入三段）

| # | 自检项 | 通过 | 依据 |
|---|--------|:---:|------|
| 1 | `synthesis_inputs` 中列出的全部 evidence 文件都已 Read 且 frontmatter 6 字段齐全 | ✅ | `<列出文件路径 + fr_refs 命中摘要>` |
| 2 | 每个 evidence 的 `signed: true`（PRE_MORTEM 强制 3 必签 + 2 触发签字 / SIGN_OFF 强制 5 评审 + 5 执行签字） | ✅ | `<逐个 role 列出已签字>` |
| 3 | 上游基线 `tds_ref` 存在且至少含 §FR 与 §验收用例两段 | ✅ | `<TDS 路径 + 段落锚点>` |
| 4 | 未发现 reviewer 之间零交集（评审产物全部指向同一组 FR） | ✅ | `<各 fr_refs 求交集结果>` |
| 5 | 未发现评审产物与已有 ADR 直接冲突（需新增 ADR 时必须列入下方"待用户确认"段） | ✅ | `<列出 adr_refs 比对>` |

> ⚠️ 任一项不通过 → 写回 `ERROR: 自检 #N 未通过 — <原因>` 并返回给 dispatcher。

---

## 一、共识条目（无需用户确认，可进入下一阶段）

> 至少 **2 个** reviewer 视角一致 + 无 ADR 冲突 + 无新依赖；
> 每条须可被 dispatcher / 下游 executor 直接引用为决策依据。

| # | 条目 | 来源 reviewer | 一致性 | 决策依据 |
|---|------|--------------|:-----:|----------|
| 1 | <条目描述，含 FR 编号 / 边界 / 实现路径> | <role1> + <role2> | ✅ | `<引用文件段落>` |
| 2 | <如：覆盖率门槛 ≥ 80%（agents/middleware）> | quality | ✅ | `<引用 GATES.md 段落>` |

> 填写要点：来源 ≥ 2 reviewer；决策依据须给可 Read 的文件 + 段落锚点（如 `TDS-M2 §5.2`）。

---

## 二、冲突条目（需 orchestrator 裁决 / 用户确认）

> reviewer 视角分歧时**必须**留条目，**不**允许 orchestrator 单方面拍板；
> 裁决建议只引用已有 ADR 或建议新增 ADR（ADR 起草动作另起 `docs/adr/ADR-XXXX.md`，此处仅占位）。

| # | 冲突点 | 视角 A | 视角 B | 裁决建议 | 状态 |
|---|--------|--------|--------|----------|:----:|
| 1 | <分歧问题> | <roleA>: <观点 + ADR 引用> | <roleB>: <观点 + ADR 引用> | **<裁决>**（依 ADR-XXXX 或建议新增 ADR-XXXX） | 待用户确认 / 已裁决 |

> 状态：`待用户确认` = 触发 §三 AskUser；`已裁决` = 已有 ADR，等待主会话确认。**不写"最终结论"，写"裁决建议"**（ORCHESTRATOR.md §七-1 红线）。

---

## 三、待用户确认条目（必须 AskUser，不允许自决）

> 任何不在 §二"已裁决"范围内的、**涉及架构 / 合规 / 商业决策**的项目**必须**列入本段；
> 一律走主会话 `AskUser` 工具（ORCHESTRATOR.md §五），不允许 orchestrator 自决。
> 一次 AskUser 最多 4 个 question；超过则**拆成多轮**。

| # | 问题 | 默认选项 | 备选 | 阻塞下一阶段 |
|---|------|----------|------|:-----------:|
| 1 | <问题陈述，含背景与影响> | <默认（带理由）> | <备选> | ✅ / ❌ |

> 一次 AskUser 最多 4 个 question（超过拆多轮）。问题必须是**是/否**或 **N 选 1** 的可决策式，不写开放问题。

---

## 四、合成退出判定（dispatcher 路由依据）

| 退出条件 | 命中 |
|----------|:---:|
| 共识条目 ≥ 1 条 | ✅ / ❌ |
| 所有冲突条目已裁决（"已裁决"或对应 AskUser 已完成） | ✅ / ❌ |
| 所有待用户确认条目已答复（AskUser 完成） | ✅ / ❌ |
| `signed: true` + 文件保存 | ✅ / ❌ |

> 全部 ✅ → 通知 dispatcher 推进；任一 ❌ → 阻塞（`signed: false`，dispatcher 不继续路由）。

---

## 五、内嵌示例（参考用）

> ⚠️ **示例中 FR-XXXX / ADR-XXXX / 路径全部为虚构演示，严禁当作真实历史引用**。
> 复制示例后必须改 `run_id`、`fr_refs`、`tds_ref`、`adr_refs`、`synthesis_inputs` 5 个字段；其它照搬骨架。
> 两示例分别覆盖：A 共识场景（3 reviewer 全一致，无冲突）+ B 冲突场景（5 reviewer，1 冲突 + 1 AskUser）。

### 例 A — 共识场景（PRE_MORTEM，3 reviewer 全一致）

#### A.1 frontmatter

```yaml
---
phase: PRE_MORTEM
run_id: demo-run-2026-07-17-fr-001-a
role: orchestrator
fr_refs: [FR-DIAG-02]
adr_refs: [ADR-0003]
synthesis_inputs:
  - 01-requirement.md
  - 02-tech-design.md
  - 03-quality.md
tds_ref: docs/spec/TDS-M2-multimodal-diagnosis.md
signed: true
---
```

#### A.2 〇、自检（全部 ✅）

| # | 自检项 | 通过 | 依据 |
|---|--------|:---:|------|
| 1 | 3 个 evidence 文件已 Read，frontmatter 6 字段齐全 | ✅ | `evidence/0[1-3]-*.md` |
| 2 | 每个 evidence `signed: true` | ✅ | requirement ✅ + tech ✅ + quality ✅ |
| 3 | `TDS-M2-multimodal-diagnosis.md` 存在且含 §FR + §验收用例 | ✅ | TDS-M2 §3 + §7 |
| 4 | 3 个 evidence 的 `fr_refs` 交集 = `{FR-DIAG-02}` | ✅ | 无零交集 |
| 5 | 未与已有 ADR 冲突 | ✅ | 仅引用 ADR-0003（多模型路由） |

#### A.3 一、共识条目

| # | 条目 | 来源 reviewer | 一致性 | 决策依据 |
|---|------|--------------|:-----:|----------|
| 1 | FR-DIAG-02 边界清晰：上传 1 张诊断图 + 异步处理 + 推送结果 | requirement + tech + quality | ✅ | TDS-M2 §3.2 |
| 2 | 异步实现走 `POST /diagnosis` → 202 + `job_id` → Redis 队列 → Worker | tech + quality | ✅ | V3 §5.6 |
| 3 | 覆盖率门槛 ≥ 80%（agents/middleware） | quality | ✅ | `coding-standards/GATES.md` L6 |
| 4 | 合规走 L1+L2 不加 L3（FR-DIAG-02 不涉及社区输出） | requirement + tech | ✅ | V3 §5.1 |

#### A.4 二、冲突条目

`无` —— 跳过整段（不留空表格，仍写"无"以示显式）

#### A.5 三、待用户确认条目

`无`

#### A.6 四、退出判定（全部 ✅）

| 退出条件 | 命中 |
|----------|:---:|
| 共识条目 ≥ 1 条 | ✅ |
| 冲突条目全部已裁决 | ✅（无） |
| 待用户确认条目全部已答复 | ✅（无） |
| `signed: true` + 文件保存 | ✅ |

→ **dispatcher 可路由到 ATDD**

---

### 例 B — 冲突 + 待用户确认场景（PRE_MORTEM，5 reviewer 全开）

#### B.1 frontmatter

```yaml
---
phase: PRE_MORTEM
run_id: demo-run-2026-07-17-fr-002-b
role: orchestrator
fr_refs: [FR-DIAG-05]
adr_refs: []
synthesis_inputs:
  - 01-requirement.md
  - 02-tech-design.md
  - 03-quality.md
  - 03b-security.md
  - 03c-devops.md
tds_ref: docs/spec/TDS-M2-multimodal-diagnosis.md
signed: true
---
```

#### B.2 〇、自检（全部 ✅）

| # | 自检项 | 通过 | 依据 |
|---|--------|:---:|------|
| 1 | 5 个 evidence 文件齐全，frontmatter 6 字段齐全 | ✅ | 5 个 `evidence/0[1-3c]-*.md` |
| 2 | 5 个 evidence `signed: true`（3 必签 + 2 触发式 sec/devops） | ✅ | req ✅ + tech ✅ + quality ✅ + sec ✅ + devops ✅ |
| 3 | `TDS-M2` 存在 + fr_refs 交集非空 + 未与 ADR 直接冲突 | ✅ | `{FR-DIAG-05}`；devops 提议新增 ADR（见 §三） |

#### B.3 一、共识条目

| # | 条目 | 来源 reviewer | 一致性 | 决策依据 |
|---|------|--------------|:-----:|----------|
| 1 | FR-DIAG-05 走异步队列，不阻塞主流程 | req + tech + quality + devops | ✅ | V3 §5.6 |
| 2 | 诊断原图 7 天后清除（含 OSS 桶 + DB 引用） | req + tech + security | ✅ | V3 §4.4 |
| 3 | 推送通道复用 `notification/scheduler`，不新增微服务 | tech + devops | ✅ | V3 §3.7 |

#### B.4 二、冲突条目

| # | 冲突点 | 视角 A | 视角 B | 裁决建议 | 状态 |
|---|--------|--------|--------|----------|:----:|
| 1 | 7 天原图是否走 CDN 边缘缓存 | security: 不缓存（PII 风险） | devops: 缓存 1 天（成本 ↓） | **不缓存**（依现有 NFR §4.4，PII 优先） | 已裁决（不阻塞） |

> ✅ 此条已裁决（依已有规范），**不**进入 §三 AskUser，dispatcher 可继续推进

#### B.5 三、待用户确认条目（须 AskUser）

| # | 问题 | 默认选项 | 备选 | 阻塞下一阶段 |
|---|------|----------|------|:-----------:|
| 1 | devops 提议新增 ADR-0018「引入 OSS 边缘缓存」是否采纳？ | **否**（V3 §4.4 已规定 PII 不缓存，无需新 ADR） | 是（起草 ADR-0018） | ✅ |

> **用户答复（YYYY-MM-DD HH:MM）**：选 "否" → §三 #1 已答复；不阻塞；exit 判定可继续。

#### B.6 四、退出判定（全部 ✅，在 AskUser 答复后）

| 退出条件 | 命中 |
|----------|:---:|
| 共识条目 ≥ 1 条 | ✅ |
| 冲突条目全部已裁决 | ✅（条目 #1 已裁决） |
| 待用户确认条目全部已答复 | ✅（AskUser 选 "否"） |
| `signed: true` + 文件保存 | ✅ |

→ **dispatcher 可路由到 ATDD**

---

## 六、参考

- 协议真源：[`agents/harness/ORCHESTRATOR.md`](../../../agents/harness/ORCHESTRATOR.md)
- evidence schema：`harness/evidence/README.md` §八（合并自原 harness-evidence Skill）
- acceptance 模板同目录：[`harness/templates/acceptance.md`](./acceptance.md)（SIGN_OFF 5 角色共识用，**不**复用本文件）
- 红线：[`.cursor/rules/project-prohibitions.mdc`](../../../.cursor/rules/project-prohibitions.mdc) R-2（业务阈值禁入 `agents/harness/`）
