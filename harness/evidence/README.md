---
name: harness-evidence
description: >
  evidence/ 目录文件命名规范 + 8 字段 frontmatter schema（V2 新增 interrupt_budget + replay_session_id）
  + 三段式结构（观点 / 论据 / 决策请求）。
  当主会话或 reviewer 需要查看/写入 evidence 文件时触发。
disable-model-invocation: false
---

# Evidence 文件规范（V2：16 phase + 8 字段）

> **唯一真源**：本 README。
> **V2 变更**：6 字段 → 8 字段（新增 `interrupt_budget` + `replay_session_id`，用于中断 budget 追踪和数据回流溯源）。
> **V1.6 兼容**：V1.6 evidence 缺少 `interrupt_budget` 和 `replay_session_id` 时，默认填充 `null`；V2 PR-Gate 验收时提供迁移默认值。

## 一、命名规范

格式：`NN-<phase-suffix>.md`

| 文件名 | 对应 phase | 作者角色 | 触发时机 |
|---|---|---|---|
| `01-requirement.md` | PRD | requirement-analyst | Phase 1 结束时 |
| `02-tech-design.md` | ARCH_DESIGN | tech-architect | Phase 2 结束时 |
| `03-pre-mortem.md` | PRE_MORTEM | orchestrator | Phase 3 合成 |
| `04-atdd.md` | ATDD | quality-guardian | Phase 4 结束时 |
| `05-plan.md` | PLAN | plan-generator | Phase 5 结束时 |
| `06-code.md` | CODE | developer | Phase 6 结束时 |
| `07-verify.md` | VERIFY | verifier | Phase 7 结束时 |
| `08-security-test.md` | SECURITY_TEST | security-reviewer | Phase 8 结束时（V2 新增） |
| `09-deploy.md` | DEPLOY | deployer | Phase 9 结束时 |
| `10-regression.md` | REGRESSION | tester | Phase 10 结束时 |
| `11-signoff.md` | SIGN_OFF | orchestrator | Phase 11 合成 |
| `12-data-replay.md` | DATA_REPLAY | requirement-analyst | Phase 12 结束时（V2 新增） |
| `13-incident-response.md` | INCIDENT_RESPONSE | deployer | Phase 13 结束时（V2 新增） |
| `14-ops-loop.md` | OPS_LOOP | tester | Phase 14 结束时（V2 新增） |
| `15-skill-update.md` | SKILL_UPDATE | quality-guardian | Phase 15 结束时（V2 新增） |
| `16-interrupt-review.md` | INTERRUPT_REVIEW | quality-guardian | 中断发生时（V2 新增） |

> W12 P2 落地前：SECURITY_TEST / DATA_REPLAY / INCIDENT_RESPONSE / OPS_LOOP / SKILL_UPDATE / INTERRUPT_REVIEW 的 evidence 暂用 `phase-checklist.md` 作为 placeholder，落地后按上表更新文件名。

## 二、Frontmatter Schema（V2 8 字段，强制）

```yaml
---
phase: <phase-id>                               # V2 16 phase 枚举
run_id: <uuid>                                   # 与 harness-state.json 的 run_id 一致
role: <role-id>                                  # 11 个角色之一
fr_refs: [<FR-XXX-XX>, ...]                    # 至少 1 个；无则填 [] 但需正文说明
adr_refs: [<ADR-XXXX>, ...]                     # 涉及技术选型时必填；无则填 []
signed: <true|false>                            # PRE_MORTEM / SIGN_OFF 必填 true
interrupt_budget: <integer>                      # V2：剩余中断次数，初始 5，每中断减 1
replay_session_id: <uuid|null>                  # V2：本轮 replay session ID（DATA_REPLAY 触发时生成）
---
```

| 字段 | 必填 | 格式 | V2 说明 |
|------|:----:|------|------|
| `phase` | ✅ | 枚举 | V2 16 phase 之一 |
| `run_id` | ✅ | UUID v4 | 与 state.json 一致 |
| `role` | ✅ | 枚举 | 11 个角色之一 |
| `fr_refs` | ✅ | 数组 | 至少 1 个 FR；无则填 `[]` |
| `adr_refs` | ⚠️ | 数组 | 涉及技术选型时必填 |
| `signed` | ⚠️ | bool | PRE_MORTEM / SIGN_OFF 必填 `true` |
| `interrupt_budget` | ✅ | integer | V2 新增：每写 evidence 时从 state.json 同步当前值 |
| `replay_session_id` | ✅ | UUID v4 | V2 新增：DATA_REPLAY phase 触发时生成；其他 phase 填 `null` |

### V1.6 → V2 迁移默认值

V1.6 evidence 缺少后两个字段时，写入者按以下规则填充：

| 缺失字段 | 默认值 | 来源 |
|----------|--------|------|
| `interrupt_budget` | `null` | V1.6 无中断机制 |
| `replay_session_id` | `null` | V1.6 无 replay 机制 |

V2 PR-Gate 在 2.3.2 兼容性检查阶段会识别 `null` 值并发出警告，不阻断合入。

## 三、三段式结构（强制）

```markdown
## 1. 观点
|（1-3 句话陈述作者的核心结论）

## 2. 论据
|（列出支撑观点的事实 / 数据 / 引用；每条 ≤ 2 行）

## 3. 决策请求
|（需要 dispatcher / orchestrator / human 做出的具体决策）
```

## 四、读写权限

| 角色 | 读 | 写 |
|---|---|---|
| 主会话 | **否**（硬性禁止，污染 8K 上下文） | 否 |
| dispatcher | 仅路由 key 引用 | 否 |
| orchestrator | 是 | `*-synthesis.md` |
| 评审/执行角色 | 自己的 + 跨评审必要引用 | 自己的 evidence |
| human | 可读全部 | 否 |

## 五、与 state.json 的联动

- 每次写 evidence 时，必须同步更新 `state/harness-state.json` 的 `phase_history[*].evidence_ref` 字段
- `interrupt_budget` 字段：进入 INTERRUPT_REVIEW 前减 1；进入新 run 时重置为 5
- `replay_session_id` 字段：进入 DATA_REPLAY 时生成新 UUID；其他 phase 继承上一 phase 的值
- PR-Gate 在 CODE → VERIFY 切换时校验：`state.json` 中声明的 evidence_ref 必须真实存在

## 六、grep 兜底（PR-Gate 补充项）

主会话在 SIGN_OFF 阶段末尾跑以下 5 条 grep（已合并到 `docs/harness/scripts/check.sh`）：

```bash
# 1. R-2 红线：agents/harness/ 禁业务阈值硬编码
grep -RnE '(if|return).*score.*[<>]=.*0\.[0-9]+' agents/harness/

# 2. evidence 文件不被主会话直接 Read（保护 8K 上下文）
grep -RnE 'evidence.*MainSession' agents/harness/ docs/harness/

# 3. evidence frontmatter 8 字段齐全
for f in docs/harness/evidence/*.md; do
  for field in phase run_id role fr_refs adr_refs signed interrupt_budget replay_session_id; do
    grep -L "^${field}:" "$f"
  done
done

# 4. SIGN_OFF evidence 必有 fr_refs 至少 1 条
grep -L "fr_refs: .*FR-" docs/harness/evidence/11-signoff.md

# 5. V2 新 phase evidence 有 replay_session_id（非 null）
grep -L "replay_session_id: null" docs/harness/evidence/12-data-replay.md
```

期望：5 条 grep 全 exit code 1（无匹配），否则触发对应红线。

## 七、严格禁止

| # | 禁止行为 | 兜底 |
|---|----------|------|
| 1 | 主会话直接 Read `evidence/*.md` 正文 | 8K 上下文约束 + grep 2 |
| 2 | 修改 `harness-state.json` 而非 orchestrator 角色 | frontmatter `role` 字段审计 |
| 3 | 缺 frontmatter 任一必填字段 | grep 3 兜底 |
| 4 | `signed: true` 但无 3 必签 + 触发式签字 | orchestrator 校验 |
| 5 | evidence 文件落点出 `docs/harness/evidence/` | pre-commit 路径 grep |
| 6 | 写 evidence 时未同步 `interrupt_budget` | dispatcher 写 state.json 时强制携带 |

## 八、与其他 Skill 边界

| Skill | 关系 |
|-------|------|
| `pr-gate/SKILL.md` | **补充项**（5 条 grep 在 CI 落地） |
| `coding-standards/SKILL.md` | **被引用**（evidence 字段命名遵循 coding-standards） |
| `golden-set/SKILL.md` | **被引用**（REGRESSION evidence 的 fr_refs 必有 `GL-*`） |
| `harness-dispatcher/SKILL.md` | **互斥**（dispatcher 只读 state 不读 evidence） |
| `harness-autolearn/SKILL.md` | **前置**（auto-learn 从 evidence 抽 lesson） |

## 九、参考

- 状态机：`docs/harness/workflow-v2.yaml`（V2 唯一真源）
- 兼容旧版：`docs/harness/workflow.yaml`（V1.6，迁移期只读）
- 角色协议：`agents/harness/REVIEWERS.md` / `EXECUTORS.md`
- grep 兜底脚本：`docs/harness/scripts/check.sh`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2
