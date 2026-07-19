# Business Routing Eval（业务路由回归）

> 本目录是 **业务路由回归**（user query → 路由 / Tier 命中）的 YAML + Runner 入口。

## ⚠️ 职责边界

| 套件 | 落点 | 形式 | 关注点 |
|------|------|------|--------|
| **拦截回归** | `backend/tests/intercept/` | pytest | `check_input()` / `check_output()` 是否漏过 / 误杀 |
| **业务路由回归**（本目录） | `backend/eval/golden_set_v1.yaml` | YAML + runner | user query → 路由 / Tier 判定 |

两套**不混装**。详见 [`backend/tests/intercept/README.md`](../tests/intercept/README.md)。

---

## 目录结构

```
backend/eval/
├── __init__.py
├── README.md                    # 本文件
├── golden_set_v1.yaml           # 业务路由 Golden Set（3 条示例）
├── runner.py                    # Eval Runner（pr / daily / release / schema 四种模式）
└── baseline.json                # Phase 0 占位 baseline
```

---

## 执行方法

```bash
# 从项目根目录运行
cd backend/eval
python -m backend.eval.runner --mode pr              # PR 抽样（默认 30 条）

# 全量跑
python -m backend.eval.runner --mode daily           # 全部用例
python -m backend.eval.runner --mode release         # 全部 + 性能基线
python -m backend.eval.runner --mode schema          # 全部 + schema 校验

# 带 baseline 对比
python -m backend.eval.runner --mode pr --baseline baseline.json

# 输出到文件
python -m backend.eval.runner --mode pr --output eval_report.json
```

---

## 四种运行模式

| 模式 | 抽样 | 触发场景 | 时间预算 |
|------|------|---------|---------|
| `pr` | 每组首条 ≥ 30 | PR open / push | < 5 分钟 |
| `daily` | 全量 | cron 02:00 | < 15 分钟 |
| `release` | 全量 + 性能基线 | release / tag | < 30 分钟 |
| `schema` | 全量 + schema 校验 | 路由表 DDL 变更后 | < 15 分钟 |

---

## 回归红线（5% drop）

任何指标（如 pass rate、Tier 2 命中率、拦截命中率）相对 `baseline.json`
跌 > 5% → PR 守门拒绝合入。

> **拦截不允许任何回归**：`intercept_block_rate_drop_pct_max = 0.0`。

判定位置：`runner.py:_compare_to_baseline` + `main()` exit code。

---

## 用例编号规范

| 前缀 | 含义 | 来源 |
|------|------|------|
| `GN-CHAT-*` | 闲聊 / 自我介绍 / 拒绝 | Phase 1 立 |
| `GN-HEALTH-*` | 健康话题路径（肩颈 / 面部 / 抱抱卡） | Phase 1 立 |
| `GN-COMPLIANCE-*` | 跨调用拦截验证（route 期望 `blocked`） | Phase 1 立 |

**禁止**：把 G-* 拦截回归 case 直接搬运到 yaml。G-* 只在 `backend/tests/intercept/`。

---

## Mock 全覆盖（Phase 1 必做）

`runner.py:_eval_against_mock` 接入真实 LangGraph 之前，所有外部依赖必须 mock：

- LLM（DashScope / Anthropic / OpenAI）
- Redis
- VectorStore
- MySQL（用户画像 / 历史记录）

禁止 `requests.get` / `httpx.AsyncClient` 等真实调用（除 GitHub Action 健康检查）。

---

## 当前状态

**Phase 0（本次落地）**：骨架 + 3 条示例 case + 占位 baseline。Runner 可跑通，
但 `_eval_against_mock` 对非拦截 case 透传 expected.route（占位语义）。

**Phase 1（后续 PR）**：
1. 接入真实 LangGraph 路由节点（替换 mock 透传）
2. 补全业务路由回归用例（≥ 30 条，覆盖闲聊 / 健康 / 跨调用拦截）
3. 重新生成 baseline.json（基于真实 Phase 1 跑测）

---

## 与其他 Skill 的边界

| Skill | 触发场景 | 本目录不做什么 |
|-------|----------|----------------|
| `coding-standards.mdc` | 改 Python 代码 → 代码质量自审 | 不查 ruff/mypy/radon |
| `golden-set/SKILL.md` | 改 yaml / 跑 runner / baseline 回归 | 不查 case 编号规范（本 README §"用例编号规范"） |
| `pr-gate/SKILL.md` | 提 PR → FR/验收测试/ADR/Commit 格式 | 不查 commit 规范 |