# L0-L6 质量门禁真源摘要

> **本文件是 L0-L6 质量门禁的"入口摘要"**——一站式给所有需要了解 L0-L6 的人（包括 AI、新成员、外部引用方）使用。
>
> **完整定义在**：[`.cursor/rules/l0-l6-gates.mdc`](../../.cursor/rules/l0-l6-gates.mdc)
>
> **审计依据**：[`harness/L0-L6-AUDIT-2026-07-19.md`](L0-L6-AUDIT-2026-07-19.md)
>
> **修复 checklist**：[`harness/checklist.md`](checklist.md) §4.5

---

## 一、为什么需要这个真源

**问题背景**（2026-07-19 审计发现）：

项目内有 22 个文件提到 L0-L6，其中 **11 个重写完整表格**。修复前出现 **5 套互相冲突的 L0-L6 定义**，最严重的是：

| 错位 | 现象 |
|------|------|
| 🔴 L2 被 Eval Runner 占用 | 3 个文档把 Eval Runner 写在 L2，my py 挤出去 |
| 🔴 L6 阈值 80% / 60% 混用 | §二写 80%，§十八/CI 跑 60% |
| 🔴 README 第 5 套错位 | 整套 L0-L6 编号全错（BDD 在 L4、locust 在 L5） |
| 🔴 AGENTS.md Backend 门禁表占 L2 | 与 R-3 表格冲突 |

**修复原则**：唯一真源（`l0-l6-gates.mdc`）+ 其他文档**引用**而非重写 + PR-Gate 卡口 7 自动拦截漂移。

---

## 二、L0-L6 一句话定义（最终版）

| 级别 | 一句话 | 工具 | 真源章节 |
|:---:|--------|------|---------|
| **L0** | 语法 & 导入验证 | py_compile + ruff check | l0-l6-gates.mdc §一 L0 |
| **L1** | 风格 & 格式化 | ruff format | l0-l6-gates.mdc §一 L1 |
| **L2** | 静态类型 | mypy strict | l0-l6-gates.mdc §一 L2 |
| **L3** | 测试（unit + integration + e2e + smoke） | pytest 全量 | l0-l6-gates.mdc §一 L3 |
| **L4** | 代码质量扫描 | ruff --select + jscpd | l0-l6-gates.mdc §一 L4 |
| **L5** | 架构 & 安全（**AI 审查 + CI 兜底**） | grep 12 条 | l0-l6-gates.mdc §一 L5 |
| **L6** | 覆盖率 ≥ 60% | pytest --cov | l0-l6-gates.mdc §一 L6 |
| **R-4** | Eval Runner（**非 L0-L6**） | python -m eval.runner --mode pr | l0-l6-gates.mdc §三 |

**核心要点**：
- **Eval Runner 不在 L0-L6 范围**——它是 R-4 红线（`project-prohibitions.mdc` R-4），仅 prompt 改动时跑。
- **L6 整体 ≥ 60%**（CI 硬卡数字）；模块级阈值见 l0-l6-gates.mdc §二。
- **L5 是 AI 审查 + CI 兜底**：developer / reviewer agent 先跑 grep 12 条；如果 AI 没拦住，CI 硬卡（backend-ci.yml L5 步骤 + PR-Gate 卡口 7）。**不靠人工**（一人 AI 开发模式无人可托）。
- **L4 双轨**：L4a = ruff 安全规则选择器（必跑）；L4b = jscpd 重复率（CI 跑）。

---

## 三、速查命令（复制即用）

```bash
# === L0 ===
python -m py_compile backend/app/xxx.py

# === L1 ===
uv run ruff check . --fix
uv run ruff format --check .

# === L2 ===
uv run mypy --strict backend/app/

# === L3 ===
uv run pytest tests/{unit,integration,e2e,smoke} -x -q

# === L4 ===
uv run ruff check . --select=F401,F811,S608,S307,SEC,B,B003
uv run jscpd backend/ --threshold 4

# === L5（AI 审查 + CI 兜底：详见 l0-l6-gates.mdc §5）===

# === L6 ===
uv run pytest --cov=app --cov-fail-under=60

# === R-4（仅 prompts/*.md 改动时跑） ===
python -m eval.runner --mode pr
```

---

## 四、修复命令记录（W4 P3 §4.5 执行）

| # | 任务 | 改的文件 | 命令摘要 |
|---|------|---------|---------|
| 4.5.1 | 修 R-3 表格 L2/L3/L4 错位 | `project-prohibitions.mdc` | StrReplace §R-3 |
| 4.5.2 | 修 §二 L6 阈值冲突 | `coding-standards.mdc` | StrReplace §二 L6 |
| 4.5.3 | 修 AGENTS.md 门禁表 | `AGENTS.md` | StrReplace 表格 |
| 4.5.4 | 创建 l0-l6-gates.mdc + 改 §二摘要 | ``.cursor/rules/l0-l6-gates.mdc``（新）+ `coding-standards.mdc` | Write 新文件 + StrReplace §二 |
| 4.5.5 | 修 CI L4 双轨 | `backend-ci.yml` | StrReplace L4 步骤 |
| 4.5.6 | ad-tdd Phase 5 加映射表 | `ad-tdd/SKILL.md` | StrReplace Phase 5 |
| 4.5.7 | 修 ARCHITECTURE L5 | `ARCHITECTURE-AND-USAGE.md` | StrReplace 第八章 |
| 4.5.8 | README + TDD-WORKFLOW 改引用 | `README.md` + `ad-tdd/TDD-WORKFLOW.md` | StrReplace 测试节 + L0-L6 引用 |
| 4.5.9 | 创建审计 + 真源摘要 | `L0-L6-AUDIT-2026-07-19.md`（新）+ `L0-L6-TRUTH.md`（新） | Write 新文件 |
| 4.5.10 | PR-Gate 卡口 7 | `pr-gate.yml` | StrReplace 添加卡口 7 |

---

## 五、引用规则（其他文档必读）

### 5.1 禁止行为

- ❌ **禁止**重写 L0-L6 完整表格（在非真源文档里）
- ❌ **禁止**把 Eval Runner 算作 L2
- ❌ **禁止**使用过期的"≥ 80%" 整体覆盖率目标
- ❌ **禁止**在 `pytest tests/unit` 上标注 L1（已合并到 L3）

### 5.2 正确引用

| 场景 | 引用文本 |
|------|---------|
| 简短引用 | "L0-L6 详见 [`.cursor/rules/l0-l6-gates.mdc`](../../.cursor/rules/l0-l6-gates.mdc)" |
| 表格引用 | "L0=py_compile / L1=ruff / L2=mypy / L3=pytest / L4=ruff+jscpd / L5=grep / L6=coverage，详见 l0-l6-gates.mdc" |
| 速查表 | 直接复制本文件 §三 的命令列表 |
| 引用本摘要 | "L0-L6 详见 [`harness/L0-L6-TRUTH.md`](L0-L6-TRUTH.md)" |

### 5.3 漂移检测

PR-Gate 卡口 7（2026-07-19 启用）会扫描所有非真源文档，若重写 L0-L6 表格 → CI 红 → 拒绝合并。

---

## 六、模块级覆盖率（l0-l6-gates.mdc §二）

| 模块 | 阈值 | 命令 |
|------|------|------|
| `rules/` | ≥ 90% | `pytest tests/unit -k rules --cov-fail-under=90` |
| `agents/` `middleware/` | ≥ 80% | 同上 |
| `tools/` | ≥ 70% | 同上 |
| **整体** | **≥ 60%** | `pytest tests/ --cov=app --cov-fail-under=60` |

**注**：模块级 `--cov-fail-under` 是 W4 P2 §4.1.3 接入改造点——首次接入仅跑整体 ≥ 60%。

---

## 七、Eval Runner 红线（l0-l6-gates.mdc §三）

> Eval Runner 不在 L0-L6 范围，但与 L0-L6 同等重要。

**触发条件**：
- 改 `backend/app/prompts/*.md`
- 改 `*.prompt` 文件
- 改 LangGraph 节点的 system prompt / user prompt

**命令**：
```bash
python -m eval.runner --mode pr
```

**门槛**：
- baseline 跌幅 > 5% → PR-Gate 拒绝
- 仅当 base >= 1 个真实基线才能合入
- 禁止 mock baseline（假阳性基线）

---

## 八、版本历史

| 日期 | 版本 | 改动 | 来源 |
|------|------|------|------|
| 2026-07-19 | v1.0 | 初次创建：项目内 L0-L6 一致性修复入口摘要 + 修复命令记录 + 引用规则 | W4 P3 §4.5.9 |

---

## 九、参考

| 文件 | 用途 |
|------|------|
| [`.cursor/rules/l0-l6-gates.mdc`](../../.cursor/rules/l0-l6-gates.mdc) | **唯一真源**——L0-L6 完整定义、命令、阈值 |
| [`harness/L0-L6-AUDIT-2026-07-19.md`](L0-L6-AUDIT-2026-07-19.md) | 审计报告——4 处严重不一致 + 3 处模糊 |
| [`harness/checklist.md`](checklist.md) §4.5 | 修复 checklist——10 个任务 P0/P1/P2 全部完成 |
| `.cursor/rules/project-prohibitions.mdc` R-3 | 红线兜底（已修复 L2/L3/L4 错位） |
| `.cursor/rules/coding-standards.mdc` §二 | alwaysApply 速查摘要 |
| `AGENTS.md` | 多 Agent 门禁表（已改引用真源） |
| `.github/workflows/backend-ci.yml` | CI L0-L4（已对齐 l0-l6-gates.mdc） |
| `.github/workflows/pr-gate.yml` | CI 守门卡口 5/6/7 |
| `agents/harness/EXECUTORS.md` §2.3 verifier | verifier 命令表（已对齐） |
