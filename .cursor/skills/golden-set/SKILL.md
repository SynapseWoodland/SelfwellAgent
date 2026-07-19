---
name: golden-set
description: >
  Golden Set 维护 + Eval Runner 使用 Skill。当修改 golden_set_v1.yaml、
  增加用例、调试 Eval Runner 失败、或评估回归 baseline 时触发。 覆盖：
  Golden Set schema 规范、用例编号（FF-* 沿用 / GN-* 新增）、real_data_anchors
  必填、Eval Runner 四种模式（pr/daily/release/schema）、baseline 回归对比、
  tuner.py 优化回路。 与 docs/重构设计方案-追问短路径与五层防线-v1.0.md 对齐。
disable-model-invocation: false
---

# Golden Set & Eval Runner Skill

## 触发条件

- 用户新增 / 修改 / 删除 `backend/eval/golden_set_v1.yaml` 用例
- 用户跑 `python -m eval.runner --mode ...`
- 用户反馈"某 case 失败"或"某 PR 触发回归红线"
- 用户提到 baseline.json / tuner.py / eval_history

## 检查清单（逐项执行）

### 1. 编号规范

- 沿用 E2E 指导书的 `FF-*` 编号（**不得重写、不得跳号**）
- 新增用例必须以 `GN-*` 前缀，编号段参见 docs §5.2
- 不允许出现 `random_001` / `test_xxx` 等无意义前缀

### 2. 字段完整性

每条用例必须 8 字段齐全：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | ✓ | 唯一编号 |
| `tier` | ✓ | 0/1/2A/2B/2C/2D/2E/3 |
| `category` | ✓ | 中文路径，单空格分隔（如"Tier2-A / 华北→华南"） |
| `query` | ✓ | 用户原话 |
| `previous_query` | ✓ | 追问时为上一问 |
| `is_followup` | ✓ | 布尔 |
| `expected.{tier, sql_template, redis_writes, ollama_calls, confidence_min}` | ✓ | 期望（闲聊/澄清用 `route`，无 `tier`） |
| `real_data_anchors[]` | ✓ | 引用真实 DB 枚举，**禁止凭印象编** |

> **判定规则（2026-06-29 修订）**：
>
> - 闲聊/澄清/insufficient → 比对 `expected.route`（不是 `tier`，因这些用例 tier 为 None）
> - Tier 1/2/3 → 比对 `actual_tier == expected.tier`
> - 全部 → 比对 `actual_confidence >= expected.confidence_min`
>
> 当前 PR-F 阶段 `_eval_against_mock` 总是返回 expected，导致全员 pass — 这是"假阳性基线"，**PR-A/B/C/D 必须实现真正的 mock 路由判定**才能让 pass 率真实。

### 3. confidence_min 阈值

- Tier 1：≥ 1.0
- Tier 2A/B/C/D/E：≥ 0.7（项目硬阈值见 `runner.py:TIER2_CONFIDENCE_THRESHOLD`）
- Tier 3 / 闲聊 / 澄清：≥ 0.0（不卡）

### 4. real_data_anchors 真实验证

每次写完必须打开 `user-mysql_meta` + `user-mysql_dw` MCP 工具，至少跑一条 `SELECT DISTINCT` 查询对应字段，把真实枚举回贴到 anchors。

不允许：
- 把"未来可能存在"的值写入 anchors
- 直接写 `dim_region IN ('华东',...)` 而没去 `SELECT DISTINCT region_name` 验证

### 5. Eval Runner 模式选择

| 场景 | 推荐模式 | 时间预算 |
| --- | --- | --- |
| PR open / push | `pr` | < 5 分钟 |
| PR merge 前 | `pr` + `e2e_real` | < 10 分钟 |
| 每日 02:00 cron | `daily` | < 15 分钟 |
| release / tag | `release` | < 30 分钟 |
| meta 库 DDL 后 | `schema` | < 15 分钟 |

### 6. 回归红线（5% drop）

任何指标（如 Tier 2 命中率、Tier 3 fallback 率、sqlglot pass rate）相对 `baseline.json` 跌 > 5% → PR 守门拒绝合入。

判定位置：`runner.py:_compare_to_baseline` + `main()` exit code。

### 7. Mock 全覆盖（PR-F 必做）

`runner.py:_eval_against_mock` 必须 mock 全部：
- MySQL meta / dw
- Redis
- Ollama
- VectorStore
- Elasticsearch

禁止 `requests.get` / `pymysql.connect` 等真实调用（除 GitHub Action 真实服务的 health check）。

### 8. tuner.py 使用约束

- ❌ 不允许自动调高 confidence 阈值绕过 LLM
- ❌ 不允许自动 commit 代码
- ✅ 必须人工 review tuner 推荐的 prompt / 规则词改动
- ✅ 历史 baseline 必须保留（rolling window ≥ 10 天）

## 输出格式

完成所有检查后，输出结构化总结：

```
## Golden Set / Eval Runner 检查结果

| 检查项 | 状态 |
| --- | --- |
| 编号规范 | ✅ / ⚠️ |
| 字段完整性 | ✅ / ⚠️ |
| confidence_min | ✅ / ⚠️ |
| real_data_anchors | ✅ / ⚠️ |
| Eval 模式 | ✅ / ⚠️ |
| 回归红线 | ✅ / ⚠️ |
| Mock 覆盖 | ✅ / ⚠️ |
| tuner 合规 | ✅ / ⚠️ |

**结论**：✅ 可以合并 / ⚠️ 请修复上述问题后再合并
```

## 触发示例

- "我加了一条用例但不知道放哪个 group"
- "跑 PR 模式看看回归吗"
- "baseline.json 这个字段是什么意思"
- "tuner 推荐的 prompt 改动能直接用吗"
- AI 主动触发（修改完 golden_set_v1.yaml 后）

## 与其他 Skill 的边界

| Skill | 触发场景 | 本 skill 不做什么 |
|-------|----------|------------------|
| `coding-standards.mdc` | 改 Python 代码 → 代码质量自审 | 不查 ruff/mypy/radon |
| `pr-gate/SKILL.md` | 提 PR → FR/验收测试/ADR/Commit 格式 | 不查 commit 规范 |
| `ad-tdd/SKILL.md` | 新增功能 → SDD→TDD 循环 | 不驱动 TDD 流程 |

---

## SelfwellAgent 当前落地状态（2026-07-04）

> 以下为本项目（SelfwellAgent）实际磁盘路径。`backend/eval/` 与 `backend/tests/intercept/` 已分流落地，**两套不混装**。

| 资产类别 | 落点路径 | 形式 | 编号 |
|----------|---------|------|------|
| **业务路由回归** | [`backend/eval/golden_set_v1.yaml`](../../backend/eval/golden_set_v1.yaml) | YAML + runner | `GN-*` |
| **业务路由 runner** | [`backend/eval/runner.py`](../../backend/eval/runner.py) | Python | — |
| **业务路由 baseline** | [`backend/eval/baseline.json`](../../backend/eval/baseline.json) | JSON | — |
| **业务路由 README** | [`backend/eval/README.md`](../../backend/eval/README.md) | Markdown | — |
| **拦截回归（输入）** | [`backend/tests/intercept/test_input.py`](../../backend/tests/intercept/test_input.py) | pytest | `G-01 ~ G-30` |
| **拦截回归（输出）** | [`backend/tests/intercept/test_output.py`](../../backend/tests/intercept/test_output.py) | pytest | `G-R/S/C-0x` |
| **拦截回归 README** | （无独立 README，整合于本 Skill §落地状态） | Markdown | — |
| **已废弃的拦截回归** | （已删除）`backend/app/services/compliance/tests/` | — | — |
| **合规检查器本体** | [`backend/services/compliance/checker.py`](../../backend/services/compliance/checker.py) | Python | — |

**关键差异（对照上方 SKILL 主体）**：

1. 本项目 `tier` 取值简化为 `0/1/2/3`（无 2A/B/C/D/E 子分类）。
2. `real_data_anchors` 引用本项目文件路径或 MCP 枚举，**不引用 SQL 表**（项目无 SQL 表）。
3. 拦截场景在 yaml 中以 `route: "blocked"` + `intercept_expectation: "critical_block"` 建模，**不放入 G-* case 集合**（G-* 仅存在于 `backend/tests/intercept/`）。
4. `runner.py:TIER2_CONFIDENCE_THRESHOLD = 0.7` 沿用 PR-F 阈值常量。

**Phase 0 当前进度**：骨架已落，3 条示例 case（GN-CHAT-001 / GN-HEALTH-001 / GN-COMPLIANCE-001），`_eval_against_mock` 对非拦截 case 透传 `expected.route`（占位语义）。Phase 1 接入真实 LangGraph 路由节点后再补真实用例与 baseline。

**目录分层（2026-07-04 方案 C 重分层后）**：

- `backend/app/` —— LangGraph / Agent / 路由节点（业务编排层，W2 填充）
- `backend/services/` —— 通用基础服务层（无业务编排）：合规检查器等
- `backend/tests/{intercept,eval}/` —— pytest 测试集（拦截回归 + 业务路由单测）
- `backend/eval/` —— 业务路由 Golden Set（YAML + Runner + baseline）

合规检查器从 `backend/app/services/compliance/` 提升到 `backend/services/compliance/`,
脱离 `app/` 业务编排依赖,future Agent 节点可直接 `from backend.services.compliance.checker import check_input`。
