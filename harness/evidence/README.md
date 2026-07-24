---
name: harness-evidence
description: >
  evidence/ 目录文件命名规范 + V3 目录结构说明
  V3 采用 templates/ + runs/ 子目录区分模板和运行产物。
disable-model-invocation: false
---

# Evidence 文件规范（V3：templates/ + runs/ 结构）

> **唯一真源**：本 README。
> **V3 变更**：新增 `templates/` + `runs/` 子目录，模板与运行产物分离。

---

## 一、V3 目录结构

```
harness/evidence/
├── templates/                   # 所有模板文件（只读）
│   ├── phase/                  # Phase Evidence 模板
│   │   ├── README.md          # 本目录说明
│   │   ├── 01-requirement.md  # REQUIREMENT 模板
│   │   ├── 02-tech-design.md  # ARCH_DESIGN 模板
│   │   ├── 03-pre-mortem.md   # PRE_MORTEM 模板
│   │   ├── 04-atdd.md         # ATDD 模板
│   │   ├── 04-tds.md          # TDS 模板（V3 新增）
│   │   ├── 05-plan.md         # PLAN 模板
│   │   ├── 06-code.md         # CODE 模板
│   │   ├── 07-verify.md       # VERIFY 模板
│   │   ├── 09-deploy.md       # DEPLOY 模板
│   │   ├── 10-regression.md   # REGRESSION 模板
│   │   └── 11-signoff.md      # SIGN_OFF 模板
│   ├── review/                 # Review Evidence 模板（V3 新增）
│   │   ├── README.md          # 本目录说明
│   │   ├── review-srs.md      # REVIEW_SRS 模板
│   │   ├── review-arch.md     # REVIEW_ARCH 模板
│   │   ├── review-atdd.md     # REVIEW_ATDD 模板
│   │   ├── review-tds.md      # REVIEW_TDS 模板
│   │   └── review-plan.md     # REVIEW_PLAN 模板
│   └── arch-clarification.md  # ARCH_CLARIFICATION 模板
├── runs/                       # 实际运行产生的证据（按 run_id 组织）
│   └── <run_id>/               # 具体某次运行的证据目录
│       ├── 01-requirement.md   # 从 templates/phase/ 复制并填写
│       ├── review-srs.md       # 从 templates/review/ 复制并填写
│       ├── 02-tech-design.md
│       ├── review-arch.md
│       ├── ...
│       └── review-plan.md
├── README.md                   # 本文件
└── .gitkeep
```

---

## 二、模板命名规范

### 2.1 Phase 模板

格式：`NN-<phase-suffix>.md`

| 文件名 | 对应 phase | 作者角色 | V3 |
|--------|------------|----------|-----|
| `01-requirement.md` | REQUIREMENT | requirement-analyst | ✅ |
| `02-tech-design.md` | ARCH_DESIGN | tech-architect | ✅ |
| `03-pre-mortem.md` | PRE_MORTEM | orchestrator | ✅ |
| `04-atdd.md` | ATDD | quality-guardian | ✅ |
| `04-tds.md` | TDS | tech-architect | **V3 新增** |
| `05-plan.md` | PLAN | plan-generator | ✅ |
| `06-code.md` | CODE | developer | ✅ |
| `07-verify.md` | VERIFY | verifier | ✅ |
| `08-security-test.md` | SECURITY_TEST | security-reviewer | ✅ |
| `09-deploy.md` | DEPLOY | deployer | ✅ |
| `10-regression.md` | REGRESSION | tester | ✅ |
| `11-signoff.md` | SIGN_OFF | orchestrator | ✅ |
| `12-data-replay.md` | DATA_REPLAY | requirement-analyst | ✅ |
| `13-incident-response.md` | INCIDENT_RESPONSE | deployer | ✅ |
| `14-ops-loop.md` | OPS_LOOP | tester | ✅ |
| `15-skill-update.md` | SKILL_UPDATE | quality-guardian | ✅ |
| `16-interrupt-review.md` | INTERRUPT_REVIEW | quality-guardian | ✅ |

### 2.2 Review 模板（V3 新增）

格式：`review-<phase-suffix>.md`

| 文件名 | 对应 Review 节点 | 审查深度 | 负责角色 |
|--------|-----------------|----------|----------|
| `review-srs.md` | REVIEW_SRS | medium | requirement-analyst |
| `review-arch.md` | REVIEW_ARCH | **heavy** | tech-architect |
| `review-atdd.md` | REVIEW_ATDD | light | quality-guardian |
| `review-tds.md` | REVIEW_TDS | medium | tech-architect |
| `review-plan.md` | REVIEW_PLAN | light | plan-generator |

### 2.3 ARCH_CLARIFICATION 模板

| 文件名 | 对应 phase | 说明 |
|--------|------------|------|
| `arch-clarification.md` | ARCH_CLARIFICATION | 3次打回后触发用户澄清 |

---

## 三、审查深度说明

| 深度 | 说明 | 适用场景 |
|------|------|----------|
| **light** | 场景格式、Given-When-Then、覆盖度 | REVIEW_ATDD, REVIEW_PLAN |
| **medium** | 加上唯一真源检查、业务/技术对齐 | REVIEW_SRS, REVIEW_TDS |
| **heavy** | 加上架构方案选择、与用户澄清 | REVIEW_ARCH |

---

## 四、Frontmatter Schema（V3 强制）

### 4.1 Phase Evidence

```yaml
---
phase: <phase-id>                               # V3 phase 枚举
run_id: <uuid>                                   # 与 harness-state.json 的 run_id 一致
role: <role-id>                                  # 角色之一
fr_refs: [<FR-XXX-XX>, ...]                    # 至少 1 个；无则填 [] 但需正文说明
adr_refs: [<ADR-XXXX>, ...]                     # 涉及技术选型时必填；无则填 []
signed: <true|false>                            # PRE_MORTEM / SIGN_OFF 必填 true
interrupt_budget: <integer>                      # 剩余中断次数，初始 5
replay_session_id: <uuid|null>                  # DATA_REPLAY 触发时生成
---
```

### 4.2 Review Evidence

```yaml
---
phase: <REVIEW_XXX>                            # Review 节点 ID
run_id: <uuid>
role: <role-id>
fr_refs: [<FR-XXX>, ...]
signed: false
review_depth: <light|medium|heavy>            # 审查深度
reviews_document: <XXX>                         # 审查的文档类型
alignment_check: <PASS|WARN|FAIL|ARCH_CLARIFICATION>
rejection_reason: null
rejection_count: 0                              # 打回次数，≥3 触发 ARCH_CLARIFICATION
---
```

### 4.3 ARCH_CLARIFICATION

```yaml
---
phase: ARCH_CLARIFICATION
run_id: <uuid>
role: tech-architect
fr_refs: [<FR-XXX>, ...]
signed: false
clarification_type: <CORE_CHANGE|SIGNIFICANT_REF_CHANGE|MINOR_REF_CHANGE>
triggering_review: <REVIEW_XXX>                # 触发澄清的 Review 节点
rejection_count: 3
options_provided: [<A>, <B>]                   # 提供的方案选项
user_approved: false
user_selected_option: null
resolution: null                                # ACCEPTED | MODIFIED | REJECTED
---
```

---

## 五、使用流程

### 5.1 新建运行

1. 创建 `runs/<run_id>/` 目录
2. 从 `templates/phase/` 复制相关模板到 `runs/<run_id>/`
3. 从 `templates/review/` 复制相关 Review 模板到 `runs/<run_id>/`
4. 填充模板内容
5. 在 `harness/state/harness-state.json` 中记录 evidence 路径

### 5.2 Review 流程

1. 进入 Review 节点时，从 `templates/review/` 复制模板
2. 执行审查，填写 `alignment_check`
3. 若 FAIL 且 `rejection_count < 3`：返回上一 phase 要求修改
4. 若 `rejection_count >= 3`：触发 `ARCH_CLARIFICATION`

---

## 六、读写权限

| 角色 | 读 | 写 |
|---|---|---|
| 主会话 | **否**（硬性禁止，污染 8K 上下文） | 否 |
| dispatcher | 仅路由 key 引用 | 否 |
| orchestrator | 是 | `*-synthesis.md` |
| 评审/执行角色 | 自己的 + 跨评审必要引用 | 自己的 evidence |
| human | 可读全部 | 否 |

---

## 七、与其他 Skill 边界

| Skill | 关系 |
|-------|------|
| `pr-gate/SKILL.md` | **补充项**（grep 在 CI 落地） |
| `coding-standards/SKILL.md` | **被引用**（evidence 字段命名遵循 coding-standards） |
| `golden-set/SKILL.md` | **被引用**（REGRESSION evidence 的 fr_refs 必有 `GL-*`） |
| `harness-dispatcher/SKILL.md` | **互斥**（dispatcher 只读 state 不读 evidence） |
| `harness-autolearn/SKILL.md` | **前置**（auto-learn 从 evidence 抽 lesson） |

---

## 八、参考

- 状态机：`harness/workflow-v3.yaml`（V3 唯一真源）
- 兼容旧版：`harness/workflow-v2.yaml`（V2，过渡期只读）
- 角色协议：`agents/harness/REVIEWERS.md` / `EXECUTORS.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2
