# GATES — 质量门禁与 CI/CD 规范

本文档是 `SKILL.md` 的子文件，质量门禁检查时加载。
所有命令均以 `backend/` 为工作目录，依赖项：`ruff`、`mypy`、`radon`、`jscpd`、`pytest`。

---

## 一、Pre-commit Hook（强制，提交前必跑）

> 来源：Quality Gate Skill（SkillMD.ai）+ nomistakes（SkillsMP）

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: ruff check .
        language: system
        types: [python]
        pass_filenames: false
      - id: ruff-format
        name: ruff format check
        entry: ruff format --check .
        language: system
        types: [python]
      - id: mypy
        name: mypy type check
        entry: mypy .
        language: system
        types: [python]
```

---

## 二、L0 — 语法 & 导入（自动，秒级）

```bash
cd backend && python -m py_compile app/xxx.py
cd backend && python -c "import app.xxx; print('OK')"
```

---

## 三、L1 — 风格 & 格式化（自动）

```bash
cd backend && uv run ruff check . --fix
cd backend && uv run ruff format --check .
```

---

## 四、L2 — 静态类型（自动）

```bash
cd backend && uv run mypy --strict app/
```

---

## 五、L3 — 单元测试（自动）

```bash
cd backend && uv run pytest tests/unit -x -q
```

---

## 六、L4 — 代码质量扫描（自动）

| 检查项 | 工具 | 阈值 / 规则 |
|--------|------|-------------|
| 圈复杂度 | `radon -a -i A` | 单函数 max A（<=10） |
| 圈复杂度均分 | `radon -a` | 平均 <= 5 |
| 代码行数 | `radon -l` | 单函数 <= 50 行 |
| 代码重复率 | `jscpd` | <= 4% |
| 未使用导入 | `ruff --select=F401` | 0 |
| 死代码 | `ruff --select=F811,F401` | 0 |
| 复制代码 | `ruff --select=F601` | 0 |
| 危险 eval | `ruff --select=S307` | 0 |
| 硬编码密钥 | `ruff --select=SEC` | 0 |
| 安全风险 | `ruff --select=B,S` | 0 |
| 可变默认参数 | `ruff --select=B003` | 0 |
| SQL 注入 | `ruff --select=S608` | 0 |
| os.system 滥用 | `ruff --select=S602,S603` | 0 |
| pickle 反序列化 | `ruff --select=S301` | 0 |
| docstring | `ruff --select=D` | 公开 API 禁止 D100/D104/D105 |

```bash
# 全部 L4 检查
cd backend && uv run ruff check . --select=F401,F811,S608,S307,SEC,B,B003
cd backend && uv run ruff format --check .
cd backend && uv run mypy --strict app/
cd backend && uv run radon -a -i A app/ | grep -v ": A$"
cd backend && uv run jscpd .
```

---

## 七、L5 — 架构 & 安全（人工审查）

| 检查项 | 方法 |
|--------|------|
| agents/ 写业务规则 | Grep `agents/` 中 if/else 业务逻辑 |
| 裸 `except:` | Grep `except:` |
| `print()` | Grep `print(` |
| 调试代码残留 | Grep `pdb.set_trace` / `breakpoint()` / `TODO` / `XXX` / `FIXME` |
| 硬编码 Prompt | Grep 节点内中文字符串 |
| 硬编码 LLM 参数 | Grep `temperature=`、`model=`、`max_tokens=` |
| 装饰器无 `@wraps` | Grep `def @` 无 `@functools.wraps` |
| 违反 ADR | 扫描 `docs/adr/*.md` |
| 未声明依赖 | 检查 `pyproject.toml` |
| **【日志】直接 import loguru** | Grep `from loguru import logger` 必须 0 命中（仅 `app/core/log.py` 与 `tests/` 测试替身可豁免） |
| **【日志】stdlib logging 绕开管道** | Grep `logging.getLogger` 必须 0 命中业务代码 |
| **【日志】PII 字段明文进日志** | Grep `\.(password\|email\|phone\|card_number\|diagnosis)\s*=` 排除 `REDACTED`/`tests/` |
| **【日志】吞 traceback** | Grep `except Exception.*logger\.warning\(str\(` 0 命中 |
| **【日志】f-string 进 message** | ruff `G004` 自动化（loguru-compat 检测） |

```bash
# L5 常用 Grep 命令
grep -rn "except:" app/
grep -rn "print(" app/
grep -rn "pdb.set_trace\|breakpoint()\|TODO\|XXX\|FIXME" app/
grep -rn "temperature=" app/
grep -rn "model=" app/

# ── L5 日志专项扫描（详见 RULES.md §五 / SKILL.md §九-日志）──
# 1. 禁止从 loguru 直接 import
grep -rn "from loguru import logger" backend/app/ && echo "FAIL: 直接 import loguru" || echo "PASS"

# 2. 禁止 stdlib logging 绕开管道（仅允许在 app/core/log.py 的 InterceptHandler 中）
grep -rn "logging\.getLogger\|logging\.basicConfig\|logging\.getLogger(__name__)" \
  backend/app/ | grep -v "app/core/log.py" && echo "FAIL: stdlib logging 旁路" || echo "PASS"

# 3. PII 字段禁入日志（黑名单 patcher 之后的人工兜底）
grep -rnE "\.(password|email|phone|card_number|diagnosis|symptom|ssn|api_key)\s*=" \
  backend/app/ \
  | grep -v "REDACTED" \
  | grep -v "tests/" \
  | grep -v "pyproject" && echo "FAIL: 可能 PII 字段进入日志" || echo "PASS"

# 4. 吞 traceback 反模式
grep -rnE "except Exception.*logger\.warning\(\s*(str\(|\{?\s*e\s*\}?)" backend/app/ \
  && echo "FAIL: 用 warning 代替 exception 吞了 traceback" || echo "PASS"

# 5. f-string 进日志（更优：交给 ruff G004 / 商用 linter）
grep -rnE "logger\.(info|warning|error|debug)\(\s*f[\"']" backend/app/ \
  && echo "WARN: f-string 进 message，可能破坏 Loki 聚合" || echo "PASS"
```

pytest fixture（放 `tests/unit/test_logging_compliance.py`，与 SDD-TDD 流程对齐）：

```python
import pytest
from app.core.log import logger

@pytest.fixture
def captured_logs():
    """Sink logs into a list for assertion."""
    sink_id = logger.add(lambda m: sink.append(m.record), format="{message}")
    sink.clear()
    yield sink
    logger.remove(sink_id)


def test_pii_blocklist_redacts(captured_logs):
    logger.bind(email="alice@example.com").info("user_queried")
    [r] = captured_logs
    assert r["extra"]["email"] == "[REDACTED]"


def test_trace_id_injected(captured_logs):
    with logger.contextualize(trace_id="abc123"):
        logger.info("chain_invoked")
    [r] = captured_logs
    assert r["extra"]["trace_id"] == "abc123"


def test_audit_events_required_fields(captured_logs):
    """§5.7 合规审计三事件必填字段。"""
    logger.warning("audit_medical_reject", user_id="pseudo", reason="...", score=0.83)
    [r] = captured_logs
    assert r["extra"]["user_id"] != "alice@example.com"   # 永远 pseudo
    assert "score" in r["extra"]
```

---

## 八、L6 — 反模式 & 设计模式（人工审查）

见 `PATTERNS.md` 中的「反模式速查表」与「设计模式速查表」。

---

## 九、四点自检清单（提交前必确认）

> 来源：Clean Code（ClawHub 465k installs）+ core-practices（SkillsMP）

每次完成代码编写后、提交前，AI 必须确认：

| 检查项 | 问题 |
|--------|------|
| ✅ Goal met? | 是否完成了用户要求的内容？不多不少？ |
| ✅ Files edited? | 是否修改了所有必要的文件？遗漏了契约文件？ |
| ✅ Code works? | 能否通过 L0-L3 自动检查？逻辑是否可验证？ |
| ✅ No errors? | Lint / type / 测试全部 PASS？ |

> 任何一项失败，必须立即修复，不允许跳过。

---

## 十、自我改进循环

> 来源：vscarpenter/coding-standards-skill（GitHub）

每次 AI 犯错或收到纠正后，主动更新项目的 `.cursorrules`：
- 记录犯的错误模式（如"忘记加 retry"、"state 用 dict"）
- 补充针对性的预防规则
- 保持 `.cursorrules` 持续演进，减少同类错误重复出现

---

## 十一、并行质量检查（可选，加速 CI）

> 来源：Quality Gate Skill（SkillMD.ai）+ nomistakes（SkillsMP）
> 若 CI 环境支持并行，可同时运行 L1+L2+L3：

```bash
# 并行执行（适用于 CI 环境）
cd backend && uv run ruff check . --fix &
cd backend && uv run ruff format --check . &
cd backend && uv run mypy --strict app/ &
cd backend && uv run pytest tests/unit -x -q &
wait
```

---

## 十二、自审报告输出格式

```
## Self-Review 检查结果

### 工具检查（L0-L4）
| 工具 | 结果 |
| --- | --- |
| py_compile | PASS / FAIL |
| ruff check | PASS / FAIL N 个 ERROR |
| ruff format | PASS / FAIL 需格式化 |
| mypy --strict | PASS / FAIL N 个错误 |
| pytest unit | PASS / FAIL N 个失败 |
| ruff quality | PASS / FAIL N 个告警 |
| radon complexity | PASS / FAIL N 个 A 级 |
| jscpd | PASS / FAIL N% 重复率 |

### 代码规范（L5-L6）
| 检查项 | 结果 |
| --- | --- |
| docstring（含 Example） | PASS / WARN N 处缺失 |
| 日志记录（统一工厂、`logger.exception`、f-string 检测） | PASS / FAIL N 处违规 |
| 日志 PII 黑名单（email/phone/card/diagnosis 字段） | PASS / FAIL N 处明文 |
| 日志合规审计三事件（safety_violation/medical_reject/persona_switch） | PASS / FAIL N 处缺失 |
| trace_id 中间件注入 | PASS / FAIL 未注册 |
| ADR 冲突 | PASS / FAIL 冲突 |
| 依赖声明 | PASS / FAIL 未声明 |
| State 类型 | PASS / FAIL N 处用 dict |
| Prompt 抽取 | PASS / FAIL N 处硬编码 |
| LLM 参数配置 | PASS / FAIL N 处硬编码 |
| 禁止项（裸 except/print/agents 规则） | PASS / FAIL N 处 |
| 反模式 | PASS / WARN N 处 |

### 结论
- **PASS**：可以提交
- **FAIL**：N 项必须修复
- **WARN**：N 项建议修复
```

---

## 十三、V1.1 工程纪律 14 条 Checklist

> 来源：`tech-arch/技术架构文档 v1.1.1` §10.4（9 条 Recall Safety / 1 人 AI 加速约束）+ §10.5（5 条工程纪律）
> 强约束：**1 人 AI 加速模式无人 code review，本节为 CI 强校验的最后兜底**。

### 13.1 14 条 Checklist（编号 = CI 检查 ID）

| # | 规则 | 检查命令 | 失败后果 | 豁免 |
|---|------|---------|---------|------|
| 1 | `from loguru import logger` 必须 0 命中 | `grep -rn "from loguru import logger" backend/app/` | CI red | 仅 `app/core/log.py` |
| 2 | `print(` 必须 0 命中 | `grep -rn "print(" backend/app/` | CI red | 测试代码 `tests/` 除外 |
| 3 | `except:` 裸 except 必须 0 命中 | `ruff check backend/app/ --select E722` | CI red | 无 |
| 4 | `except Exception` 必须前置捕获 `asyncio.CancelledError` | `ruff check backend/app/ --select ASYNC101` | CI red | 同步函数除外 |
| 5 | 所有 agent 节点必须用 `class AgentState(TypedDict)` 不用 dict | `grep -rn ": dict" backend/app/agents/*/state.py` | CI red | 无 |
| 6 | 所有 prompt 必须抽到 `app/prompts/`，业务代码不得 f-string 拼 prompt | `grep -rn "f\".*{.*}.*\".*system\|f\".*{.*}.*\".*prompt" backend/app/agents/` | CI red | j2 模板内允许 |
| 7 | 所有 LLM 参数（model/temperature/max_tokens）必须从配置读 | `grep -rn "model=\".*\"\|temperature=0\." backend/app/services/llm/` | CI red | `app/conf/llm.py` 除外 |
| 8 | 所有依赖必须在 `pyproject.toml` 声明 | `uv pip check && python -c "import tomllib; ..."` | CI red | 无 |
| 9 | 所有错误码字符串必须 `from app.errors.codes import E_*` | `grep -rn 'E_[A-Z_]\+\s*=\s*"' backend/app/` | CI red | 仅 `app/errors/codes.py` |
| 10 | 所有 Pydantic 模型必须有 docstring | `ruff check backend/app/ --select D102` | CI red | 内部 helper 除外 |
| 11 | 所有 service 函数必须有 docstring | `ruff check backend/app/services/ --select D102` | CI red | 私有函数除外 |
| 12 | 复杂度：函数 McCabe ≤ 10，类 ≤ 20 | `radon cc backend/app/ -a -s` | CI red | 入口函数豁免 |
| 13 | 重复率：`jscpd` ≤ 3% | `jscpd backend/app/ --threshold 3` | CI red | 无 |
| 14 | 测试覆盖率：新代码 ≥ 80% | `pytest --cov=backend/app --cov-fail-under=80` | CI red | 工具类除外 |

### 13.2 跑全部 14 条（合并脚本）

```bash
#!/usr/bin/env bash
# backend/scripts/check_14.sh —— CI 入口
set -e
echo "[1/14] loguru import 检查..."  && grep -rn "from loguru import logger" backend/app/ | grep -v "app/core/log.py" | grep -q . && exit 1 || true
echo "[2/14] print 检查..."          && grep -rn "print(" backend/app/ | grep -q . && exit 1 || true
echo "[3/14] 裸 except 检查..."      && ruff check backend/app/ --select E722
echo "[4/14] CancelledError 前置..." && ruff check backend/app/ --select ASYNC101
echo "[5/14] AgentState TypedDict..." && grep -rn ": dict" backend/app/agents/*/state.py && exit 1 || true
echo "[6/14] f-string prompt 检查..." && grep -rn 'f".*{.*}.*".*system\|f".*{.*}.*".*prompt' backend/app/agents/ && exit 1 || true
echo "[7/14] LLM 参数硬编码..."       && grep -rn 'model="[^"]*"\|temperature=0\.' backend/app/services/llm/ | grep -v "app/conf/llm.py" && exit 1 || true
echo "[8/14] 依赖声明..."            && uv pip check
echo "[9/14] 错误码导入..."           && grep -rn 'E_[A-Z_]\+\s*=\s*"' backend/app/ | grep -v "app/errors/codes.py" && exit 1 || true
echo "[10/14] Pydantic docstring..."  && ruff check backend/app/ --select D102
echo "[11/14] service docstring..."   && ruff check backend/app/services/ --select D102
echo "[12/14] McCabe 复杂度..."       && radon cc backend/app/ -a -s
echo "[13/14] jscpd 重复率..."        && jscpd backend/app/ --threshold 3
echo "[14/14] 测试覆盖率..."          && pytest --cov=backend/app --cov-fail-under=80
echo "ALL 14 CHECKS PASSED ✓"
```

### 13.3 反模式

| 坏味道 | 后果 | 正确做法 |
|--------|------|----------|
| 14 条只写不跑 | 形同虚设 | CI 必跑 `scripts/check_14.sh` |
| 豁免滥用（PR 频繁加豁免）| 规则变成摆设 | 豁免必须有 owner + 过期时间 + ADR 引用 |
| 不区分 §13.1 vs §13.2 | 命令散落 | 全部走 `check_14.sh` 入口 |
| 跳过 §14 覆盖率（"来不及写测试"）| 技术债累积 | CI 必须 ≥ 80%，否则不允许 merge |
| §6 f-string 检查只 grep `f"{` 不覆盖 `f'{'` | 漏过单引号 | 检查命令覆盖 4 种引号组合 |

### 13.4 自审命令

```bash
# L4：14 条脚本必须存在
test -x backend/scripts/check_14.sh && echo OK
# L5：14 条逐一可执行（dry-run）
bash -n backend/scripts/check_14.sh
# L6：每周一全量跑
python backend/eval/run_eval.py --mode weekly --suite engineering_discipline
```
