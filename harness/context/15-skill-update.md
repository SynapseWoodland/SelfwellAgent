---
name: harness-context-skill-update
description: >
  SKILL_UPDATE phase context template。V2 新增 phase。
  当 dispatcher 路由到 SKILL_UPDATE 时由 quality-guardian 角色 Read。
disable-model-invocation: true
---

# SKILL_UPDATE Phase Context

> **V2 新增 phase**。OPS_LOOP 完成后进入 SKILL_UPDATE，由 quality-guardian 执行 lesson → pattern → instinct 三级晋升评审。

## 一、必读

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `evidence/14-ops-loop.md` | OPS_LOOP phase 产出，确认本轮指标 |
| 2 | `evidence/11-signoff.md` | SIGN_OFF phase 产出，确认完整交付物 |
| 3 | `harness/lessons/` | 本轮 lesson 库 |
| 4 | `harness/patterns/` | 已有 pattern 库（用于判断是否晋升） |
| 5 | `harness-autolearn` skill | `.cursor/skills/harness-autolearn/SKILL.md` |

## 二、禁止

| 禁止行为 | 原因 |
|----------|------|
| 在无 lesson 积累时强制晋升 | 晋升必须有实证 |
| 跳过 INTERRUPT_REVIEW 直接进入新 PRD | SKILL_UPDATE 后必须有一次追问日志检查 |
| 修改 `backend/app/rules/` | instinct = 永久性规则，修改需通过正式评审 |

## 三、必产物

| 产物 | 文件路径 | 说明 |
|------|----------|------|
| 技能更新证据 | `evidence/15-skill-update.md` | 8 字段 frontmatter + 三段式 |
| lesson 沉淀 | `harness/lessons/` 下新建本轮 lesson | 1-3 条 |
| pattern 晋升判断 | 在 evidence 正文中记录判断结果 | 晋升 / 不晋升 / 待观察 |

### SKILL_UPDATE Checklist

| 检查项 | 操作 |
|--------|------|
| lesson 提取 | 从本轮 evidence 中提取 1-3 条可复用的教训 |
| lesson → pattern 晋升判断 | 同一 pattern 下是否有 ≥3 次相似 lesson → 晋升 |
| pattern → instinct 晋升判断 | 同一 instinct 下是否有 ≥5 次相似 pattern → 晋升 |
| instinct 写入 | 若晋升，生成 instinct YAML 并写入 `backend/app/rules/` |
| 阈值检查 | 确认晋升阈值未被绕过（harness-autolearn skill 强制） |

### 晋升阈值（harness-autolearn 强制）

| 晋升 | 阈值 | 证据位置 |
|------|------|----------|
| lesson → pattern | 同一 pattern 出现 ≥3 次相似 lesson | `harness/lessons/` + `harness/patterns/` |
| pattern → instinct | 同一 instinct 出现 ≥5 次相似 pattern | `harness/patterns/` + `backend/app/rules/` |

## 四、退出条件

SKILL_UPDATE 退出必须同时满足：

1. ✅ `evidence/15-skill-update.md` 已写入，`signed: true`
2. ✅ lesson 已沉淀到 `harness/lessons/`
3. ✅ 晋升判断已记录（无论晋升与否）
4. ✅ instinct（若有）已写入 `backend/app/rules/`
5. ✅ `next_phase_hint` = `"INTERRUPT_REVIEW"` 已写入 state.json

## 五、与其他 phase 的关系

```
OPS_LOOP ──(验证通过)──> SKILL_UPDATE ──(完成后)──> INTERRUPT_REVIEW ──(完成后)──> DATA_REPLAY ──> PRD（新一轮）
                                                ↑
                                       quality-guardian 签字
```

## 六、参考

- workflow-v2.yaml：`harness/workflow-v2.yaml`
- evidence schema：`harness/evidence/README.md`
- harness-autolearn skill：`.cursor/skills/harness-autolearn/SKILL.md`
- 红线：`.cursor/rules/project-prohibitions.mdc` R-2 / R-5
