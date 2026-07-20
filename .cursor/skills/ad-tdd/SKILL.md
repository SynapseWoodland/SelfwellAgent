---
name: ad-tdd
description: >
  根据 harness/atdd/ 目录下的 ATDD 文档，执行 TDD 循环开发。
  仅负责 CODE 阶段的 TDD 循环（RED → GREEN → REFACTOR），不涉及流程编排。
  TDD 循环中只做 Unit Test；其他测试在 VERIFY/REGRESSION 阶段进行。
trigger: >
  - 用户进入 CODE 阶段 / 说"开始开发"、"TDD 开发"、"实施代码"
  - 已有 harness/atdd/*.md 文档
disable-model-invocation: false
---

# TDD 开发流（基于 ATDD）

> **职责边界**：本 Skill 只负责 CODE 阶段的 TDD 循环。
> - ATDD 文档生成 → 由 Harness ATDD phase 负责
> - Integration/API-E2E/Smoke/UI-E2E 测试 → 由 Harness VERIFY/REGRESSION 阶段负责
> - Sign-off → 由 pr-gate skill 负责

---

## 一、输入

1. **ATDD 文档**：`harness/atdd/ATDD-M*.md`（Gherkin 场景）
2. **技术设计**：`docs/spec/TDS-M*.md`
3. **编码规范**：`.cursor/rules/coding-standards.mdc`
4. **L0-L6 门禁**：`.cursor/rules/l0-l6-gates.mdc`

---

## 二、TDD 循环

对 ATDD 中每个 Scenario，执行以下循环：

```
RED（写测试） → GREEN（写实现） → REFACTOR（重构）
```

### Step 1 — RED：写测试

**规则**：
- 测试文件：`backend/tests/unit/test_<模块>_<场景>.py`
- 先断言 `from app.xxx import yyy` 能导入（验证模块存在）
- 验证 RED 真有效：`pytest` 退出码 = 1 + 含 `AssertionError`

**命令**：
```bash
cd backend
uv run pytest tests/unit/test_<feature>.py -x --tb=line
```

**禁止**：
- ❌ 先写实现后补测试
- ❌ 测试依赖实现细节（测行为，不测实现）

### Step 2 — GREEN：写实现

**规则**：
- 文件放 `backend/app/` 对应模块
- 遵循 `coding-standards.mdc` 目录边界约束
- **Agent State 必须继承 TypedDict**（不要用 dict，不要用 Pydantic BaseModel 作为 State）
- 节点签名：`async def node(state: AgentState, runtime: Runtime[AgentContext]) -> dict`
- 节点内禁止直接修改 state，**必须返回增量 dict**
- 配置从 `app_config` 读取，禁止硬编码

**禁止假绿**：
- ❌ `return []` / `return None` / `return {}` 直接绕过逻辑
- ❌ `pass` / `NotImplementedError` / `raise TODO`
- ❌ `try/except: pass` 全吞
- ❌ magic number 0/1 绕过 LLM
- ✅ 必须有真实业务逻辑（即使再简单）

### Step 3 — REFACTOR：重构

**规则**：
- 单函数 ≤ 50 行，单节点 ≤ 150 行
- 圈复杂度 ≤ 10
- 嵌套深度 ≤ 4 层
- 测试全程保持 PASS

**重构时同步更新**：
- docstring（Google 风格，含 Example）
- 日志（`from app.core.log import logger`）

---

## 三、复杂度约束

| 约束 | 阈值 | 检查命令 |
|------|------|---------|
| 单函数行数 | ≤ 50 | `uv run radon -l backend/app/` |
| 单节点行数 | ≤ 150 | 同上 |
| 圈复杂度 | ≤ 10 | `uv run radon -a -i A backend/app/` |
| 嵌套深度 | ≤ 4 | `uv run ruff check . --select=PLR1702` |
| 参数数量 | ≤ 5 | `uv run ruff check . --select=PLR0913` |

---

## 四、完成后

1. **Unit Test 全量**：`cd backend && uv run pytest tests/unit -x -q`
2. **覆盖率**：`cd backend && uv run pytest --cov=app --cov-fail-under=60`
3. **进入 Harness VERIFY 阶段**

---

## 五、参考

| 文档 | 路径 |
|------|------|
| ATDD 文档 | `harness/atdd/ATDD-M*.md` |
| 技术设计 | `docs/spec/TDS-M*.md` |
| 编码规范 | `.cursor/rules/coding-standards.mdc` |
| L0-L6 门禁 | `.cursor/rules/l0-l6-gates.mdc` |

---

## 六、测试分层说明

| 测试类型 | 执行阶段 | 负责 Skill |
|---------|---------|-----------|
| **Unit Test** | TDD 循环（CODE） | 本 Skill |
| **Integration** | VERIFY / REGRESSION | Harness VERIFIER |
| **API-E2E** | VERIFY / REGRESSION | Harness VERIFIER |
| **Smoke** | VERIFY / REGRESSION | Harness VERIFIER |
| **UI-E2E** | VERIFY / REGRESSION | Harness TESTER |

> UI-E2E 使用微信开发者工具 MCP，详见 `docs/cursor_experience/wechat-devtools-mcp-debugging.md`
