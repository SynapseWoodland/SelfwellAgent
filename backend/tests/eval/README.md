# 拦截回归（Intercept Regression）

> 本目录存放 Selfwell 合规**拦截回归**用例（G-* 编号）。

## 职责边界（与业务路由回归分流）

| 套件 | 落点 | 形式 | 关注点 |
|------|------|------|--------|
| **拦截回归**（本目录） | `backend/tests/intercept/` | pytest 参数化 | `check_input()` / `check_output()` 是否漏过 / 误杀 |
| **业务路由回归** | `backend/eval/golden_set_v1.yaml` | YAML + runner | 用户问句 → 路由 / Tier 命中 |

两套**不混装**:拦截判定为单元级断言,路由判定需 mock 全栈 + baseline 对比,
场景数量级、跑测时间、外部依赖都不同。

---

## 目录结构

```
backend/tests/intercept/
├── __init__.py
├── conftest.py                # 防御性 sys.path 兜底
├── test_input.py              # 输入拦截测试（用户 → 系统）
├── test_output.py             # 输出检测测试（LLM 输出 → 用户）
└── README.md                  # 本文件
```

---

## 执行方法

```bash
# 从项目根目录运行
pytest backend/tests/intercept -v

# 只跑输入拦截
pytest backend/tests/intercept/test_input.py -v

# 只跑输出检测
pytest backend/tests/intercept/test_output.py -v

# 带覆盖率
pytest backend/tests/intercept/ \
    --cov=backend.app.services.compliance \
    --cov-report=term-missing
```

---

## 测试通过标准

| 指标 | 目标 | 触发告警 |
|------|------|---------|
| 拦截准确率 | 100%（G-01~G-12 必须全部被 block） | < 100% |
| 通过准确率 | 100%（G-13~G-22 必须全部被 pass） | < 100% |
| 边界准确率 | 100%（G-23~G-30 符合预期分级） | < 100% |
| LLM 输出违规 | 0（G-R/S/C-0x 系列 100% 合规） | > 0 |
| 漏过率 | 0% | > 0% |

**任何一项不达标 → 本次提交阻塞，不允许合入主干。**

---

## Case 编号规范

| 前缀 | 含义 | 来源 |
|------|------|------|
| G-01 ~ G-12 | 必须拦截类（医疗/医美/承诺） | ADR-0004 §7 |
| G-13 ~ G-22 | 合法通过类（正常描述） | ADR-0004 §7 |
| G-23 ~ G-30 | 边界类（警告或通过） | ADR-0004 §7 |
| G-R-0x | LLM 诊断报告输出 | §3.3 AI 诊断 |
| G-S-0x | AI 督促话术 | §4.2 打卡话术 |
| G-C-0x | 抱抱卡文案 | §4.3 抱抱卡 |

---

## 新增 Case 流程

1. 在 `test_input.py` 或 `test_output.py` 中新增 case
2. 标注 `id=`（格式：`G-XX 描述`）
3. 运行测试确认通过
4. 更新本 README 的 case 数量统计
5. PR 中说明新增 case 的理由

> 路由层用例（"哪些自然语言 → 哪个 tier"）请放 `backend/eval/golden_set_v1.yaml`，
> 不在本目录范围内。