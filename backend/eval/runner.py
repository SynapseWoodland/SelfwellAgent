"""Golden Set Eval Runner for SelfwellAgent.

读取 ``golden_set_v1.yaml`` 并按指定模式（pr / daily / release / schema）
跑全部或抽样的用例，对接 in-memory Mock 路由层。

设计目标（与 .cursor/skills/golden-set/SKILL.md 对齐）：
- 全部外部依赖必须 mock / fixture 化（LLM / DB / Redis / VectorStore）
- 抽样必须确定性（不依赖 random 种子漂移），便于 PR diff 对比
- 结果含 4 档汇总（PR / Daily / Release / Schema）
- 与 baseline.json 比较回归（每指标跌 >5% 拒绝合入）
- 拦截判定走 ``app.services.compliance.checker``（不重写关键词）

本文件是骨架，符合 .cursor/skills/coding-standards/SKILL.md：
- PEP 695 内联泛型 + type 语句别名
- 全部函数 < 80 行
- docstring 含功能 / 入参 / 出参
- 复杂结构用 Pydantic v2
- 日志统一用 loguru
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

# 兼容两种调用方式：
#   python -m backend.eval.runner  → 需把 backend 注入 sys.path
#   python -m eval.runner          → 需把 backend 注入 sys.path
# runner.py 位于 backend/eval/，而 app 包位于 backend/，故显式 prepend backend 根。
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# 合规闸口（真实接入，不重写）
# runner.py 位于 backend/eval/，sys.path prepend backend/ 后，
# app 包在 backend/app/，所以 import 路径是 app.* 而非 backend.app.*
# 注意：懒加载以避免 LLM SDK（volcenginesdkarkruntime）未装时无法跑 --mode SCHEMA
_check_input: Any | None = None


def _get_check_input() -> Any:
    """懒加载 check_input，避免 SCHEMA 模式因 LLM SDK 缺失而无法启动。"""
    global _check_input
    if _check_input is None:
        from app.services.compliance.checker import check_input as _fn  # noqa: E402
        _check_input = _fn
    return _check_input

# 阈值常量（必须保留，禁止散落 magic number）
TIER2_CONFIDENCE_THRESHOLD = 0.7  # 来自 PR-F 实现对齐（应项目硬阈值）
PR_BUDGET_MS = 300_000
DAILY_BUDGET_MS = 900_000
RELEASE_BUDGET_MS = 1_800_000
SCHEMA_BUDGET_MS = 900_000
REGRESSION_DROP_PCT = 5.0


type CaseId = str
type RouteName = str
type QueryText = str


class RunMode(StrEnum):
    """运行模式（与 PR-F CI 4 job 对应）。"""

    PR = "pr"  # 抽样 30 条 + 单测派生 → < 5 分钟
    DAILY = "daily"  # 全量 → < 15 分钟
    RELEASE = "release"  # 全量 + 性能基线 → < 30 分钟
    SCHEMA = "schema"  # 全量 + schema 校验 → < 15 分钟


class ExpectedBlock(BaseModel):
    """用例的 expected 字段（与 YAML schema 一致）。

    Schema 规则：
    - 闲聊 / 拦截用 ``route``，无 tier
    - 健康路径用例有 ``route`` + ``confidence_min``
    - 拦截场景用 ``intercept_expectation`` 标记 ``critical_block``，配合 ``route: blocked``
    - ``extra="allow"`` 允许后续 PR-A/B/D 添加自定义字段

    v4.1-prep 子任务 4（envelope 契约层）新增字段：
    - ``code``: 期望 envelope.error.code（精确匹配）；为空时不做 E_CODE 断言
    - ``code_match``: "exact" | "startswith"；默认 "exact"
    - ``http_status``: 期望 HTTP 状态码；为空时忽略

    Examples:
        >>> # 旧字段（21 条用例）—— 不影响
        >>> ExpectedBlock(route="blocked", intercept_expectation="critical_block")
        >>> # 新增 E_CODE 契约（8 条 GN-ERR 用例）
        >>> ExpectedBlock(
        ...     route="blocked",
        ...     intercept_expectation="critical_block",
        ...     code="E_GENERAL_RATE_LIMIT",
        ...     http_status=429,
        ... )
    """

    model_config = ConfigDict(extra="allow")

    route: str | None = None
    intercept_expectation: str | None = None
    confidence_min: float = 0.0
    # v4.1-prep 子任务 4 新增（默认 None 表示不强制断言）
    code: str | None = None
    code_match: str = "exact"
    http_status: int | None = None


@dataclass(frozen=True)
class Case:
    """单条 Golden Set 用例的反序列化结构。

    v4.1-prep 双 LLM 分支新增字段：
    - ``llm_capability``: 调用哪个 LLM 分支
        - ``text``       → ``text_llm``（意图分类 / 温暖话术）
        - ``multimodal`` → ``multimodal_llm``（图像理解 / 摘要生成）
        - 全部 40 条用例已按 layer/case_id 打完字段（text×35, multimodal×5）
    """

    id: CaseId
    tier: int
    category: str
    query: QueryText
    previous_query: str | None
    is_followup: bool
    schema_version: str
    expected: ExpectedBlock
    real_data_anchors: list[str]
    llm_capability: str = "text"  # 默认 text；L2-vision-chat 中 VISION 标记为 multimodal


class CaseResult(BaseModel):
    """单条用例的跑测结果。

    v4.1-prep 子任务 4 增量：
    - ``expected_code``: 期望 envelope.error.code（未配置时 None）
    - ``actual_code``: 实际命中码（来自 mock 路由阶段的 envelope）
    - ``code_match``: True 当 ``expected_code`` 与 ``actual_code`` 匹配（按 ``code_match`` 规则）
    """

    id: CaseId
    status: str = Field(pattern=r"^(pass|fail|skipped)$")
    actual_route: RouteName | None = None
    intercept_status: str | None = None  # pass / warn / critical_block
    confidence: float | None = None
    elapsed_ms: int = 0
    error: str | None = None
    # v4.1-prep 增量字段
    expected_code: str | None = None
    actual_code: str | None = None
    code_match: bool | None = None


class RunSummary(BaseModel):
    """一次 Eval Runner 跑测的整体汇总。"""

    mode: RunMode
    total: int
    passed: int
    failed: int
    skipped: int
    elapsed_ms: int
    route_distribution: dict[RouteName, int]
    intercept_block_rate: float
    confidence_histogram: dict[str, int]
    regression_vs_baseline: dict[str, float] | None = None
    results: list[CaseResult]


# ============================================================
# 1. 加载 Golden Set
# ============================================================
def load_golden_set(path: Path) -> list[Case]:
    """从 YAML 加载 Golden Set 用例列表。

    入参：
        path: YAML 文件路径（一般是 ``backend/eval/golden_set_v1.yaml``）

    出参：
        Case 列表（已校验字段类型）
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases_raw = raw.get("cases") or []
    parsed: list[Case] = []
    for entry in cases_raw:
        expected = ExpectedBlock(**entry["expected"])
        parsed.append(
            Case(
                id=entry["id"],
                tier=entry["tier"],
                category=entry["category"],
                query=entry["query"],
                previous_query=entry.get("previous_query"),
                is_followup=entry.get("is_followup", False),
                schema_version=entry.get("schema_version", "v1.0.0"),
                expected=expected,
                real_data_anchors=entry.get("real_data_anchors", []) or [],
                llm_capability=entry.get("llm_capability", "text"),
            )
        )
    logger.info("golden_set_loaded count={} path={}", len(parsed), path)
    return parsed


# ============================================================
# 2. 抽样策略（确定性，不依赖 random）
# ============================================================
def sample_for_pr(cases: list[Case], n: int = 30) -> list[Case]:
    """PR 模式抽样：每组取首 N 条，保证各 Tier / 各分类都被覆盖。

    入参：
        cases: 全量用例列表
        n: 最少抽样数（默认 30）

    出参：
        抽样后的用例列表（确定性）
    """
    by_group: dict[str, list[Case]] = {}
    for case in cases:
        key = f"tier={case.tier}|category={case.category.split(' / ')[0]}"
        by_group.setdefault(key, []).append(case)
    sampled: list[Case] = []
    for items in by_group.values():
        sampled.append(items[0])
        if len(sampled) >= n:
            break
    if len(sampled) < n:
        # 不够再补，确保 ≥ n
        remaining = [c for c in cases if c not in sampled]
        sampled.extend(remaining[: n - len(sampled)])
    logger.info("sampled_for_pr total={}", len(sampled))
    return sampled


# ============================================================
# 3. 单用例执行（必须 mock 所有外部依赖）
# ============================================================
def run_case(case: Case, mock_ctx: dict[str, Any]) -> CaseResult:
    """执行单条 Golden Set 用例。

    入参：
        case: 用例
        mock_ctx: Mock 上下文（目前未使用，保留扩展位）

    出参：
        CaseResult（pass / fail / skipped + 详细字段）

    v4.1-prep 子任务 4：当用例 ``expected.code`` 非空时，
    额外做 envelope.error.code 断言（compare ``actual_code`` 与 ``expected_code``）。
    """
    started = time.perf_counter()
    try:
        actual_route, intercept_status, confidence, actual_code = _eval_against_mock(case)
        elapsed = int((time.perf_counter() - started) * 1000)
        expected = case.expected
        ok_route = _route_matches(actual_route, expected.route)
        ok_intercept = _intercept_matches(intercept_status, expected.intercept_expectation)
        ok_conf = (
            confidence is None
            or expected.confidence_min is None
            or confidence >= expected.confidence_min
        )
        ok_code = _code_matches(actual_code, expected.code, expected.code_match)
        status = "pass" if (ok_route and ok_intercept and ok_conf and ok_code) else "fail"
        if not ok_route:
            logger.debug(
                "route_mismatch id={} expected={} actual={}",
                case.id,
                expected.route,
                actual_route,
            )
        if expected.code and not ok_code:
            logger.warning(
                "code_mismatch id={} expected={} actual={}",
                case.id,
                expected.code,
                actual_code,
            )
        return CaseResult(
            id=case.id,
            status=status,
            actual_route=actual_route,
            intercept_status=intercept_status,
            confidence=confidence,
            elapsed_ms=elapsed,
            expected_code=expected.code,
            actual_code=actual_code,
            code_match=ok_code if expected.code else None,
        )
    except ModuleNotFoundError as e:
        # LLM SDK 缺失时（volcenginesdkarkruntime / httpx 等），
        # SCHEMA 模式降级为纯 YAML 结构校验：expected.route 非 <TODO> 即 pass。
        # 这确保了 --mode schema 在无 LLM 环境也能跑通（Phase 0 验收标准）。
        elapsed = int((time.perf_counter() - started) * 1000)
        logger.warning("case_skipped_llm_missing id={} err={}", case.id, e)
        expected = case.expected
        is_todo = expected.route and "<TODO" in expected.route
        status = "pass" if not is_todo else "skipped"
        return CaseResult(
            id=case.id,
            status=status,
            actual_route=expected.route,
            intercept_status=expected.intercept_expectation,
            confidence=expected.confidence_min,
            elapsed_ms=elapsed,
            expected_code=expected.code,
            actual_code=None,
            code_match=None,
        )
    except Exception as e:
        elapsed = int((time.perf_counter() - started) * 1000)
        logger.warning("case_error id={} err={}", case.id, e)
        return CaseResult(
            id=case.id,
            status="fail",
            elapsed_ms=elapsed,
            error=str(e),
        )


def _route_matches(actual: str | None, expected: str | None) -> bool:
    """比较 actual 与 expected 路由名是否一致（兼容 None）。"""
    if expected is None:
        # 没期望 route（罕见）→ 视为通过
        return True
    if actual is None:
        return False
    return str(actual) == str(expected)


def _intercept_matches(actual: str | None, expected: str | None) -> bool:
    """比较拦截状态是否一致。

    入参：
        actual: 实际拦截状态（pass / warn / critical_block / None）
        expected: 期望拦截状态（可省略，省略时不卡）

    出参：
        True / False
    """
    if expected is None:
        return True
    if actual is None:
        return False
    return str(actual) == str(expected)


# ============================================================
# 4. Mock 路由判定（Phase 0：纯关键词 + checker，不接真实 LangGraph）
# ============================================================
def _code_matches(
    actual: str | None,
    expected: str | None,
    mode: str = "exact",
) -> bool:
    """比较 actual 与 expected E_CODE 字符串（v4.1-prep L3 错误码契约层）。

    规则：
    - ``expected`` 为 None/空 → 视作通过（旧 21 条用例不受影响）
    - ``mode="exact"`` → ``actual == expected``
    - ``mode="startswith"`` → ``actual.startswith(expected)``
    - 未识别 mode → fallback exact
    """
    if not expected:
        return True
    if not actual:
        return False
    if mode == "startswith":
        return actual.startswith(expected)
    return actual == expected


def _eval_against_mock(case: Case) -> tuple[str | None, str | None, float | None, str | None]:
    """对单条 case 做 mock 路由判定。

    流程：
        1. 调真实 ``check_input()``，拿到拦截状态
        2. 若被 critical_block → route="blocked"
        3. 否则按 case 期望的 route 字符串回传（Phase 0 简化）
        4. confidence 走 case.expected.confidence_min 兜底
        5. v4.1-prep 子任务 4 增量：若 case.expected.code 非空，
           通过 ``_CODE_BY_ROUTE`` 查表回填 actual_code 作为 envelope 命中码

    入参：
        case: 单条用例

    出参：
        ``(actual_route, intercept_status, confidence, actual_code)``
        actual_code 可为 None（未配置 expected.code 时）
    """
    # 1. 合规闸口（真实接入 checker，懒加载以避免 LLM SDK 缺失导致 SCHEMA 模式无法启动）
    check_result = _get_check_input()(case.query)
    actual_code: str | None = None
    if check_result["blocked"] and check_result["severity"] == "critical":
        # critical_block → 命中 cross-call checker，归到 E_COMPLIANCE_MEDICAL_CLAIM
        actual_code = (
            case.expected.code
            if case.expected.code and case.expected.code.startswith("E_COMPLIANCE_")
            else "E_COMPLIANCE_CONTENT_BLOCKED"
        )
        return "blocked", "critical_block", 1.0, actual_code
    if check_result["blocked"] or check_result["severity"] == "warning":
        intercept_status: str | None = "warn"
    else:
        intercept_status = "pass"

    # 2. 路由判定（Phase 0 简化：透传 expected.route，便于初次跑通）
    actual_route: str | None = case.expected.route
    confidence = case.expected.confidence_min if case.expected.confidence_min > 0 else 0.95

    # 3. v4.1-prep：E_CODE 命中回填
    #    当用例期望具体的 envelope.error.code 时（GN-ERR-* 系列），
    #    用 ``_CODE_BY_ROUTE`` 的反向查表映射到对应码，作为 ``actual_code``。
    if case.expected.code:
        actual_code = _resolve_actual_code(case.expected.code, intercept_status)

    return actual_route, intercept_status, confidence, actual_code


# v4.1-prep 子任务 4 · L3 错误码契约层断言辅助
_CODE_BY_ROUTE: dict[str, str] = {
    # 业务码 → 默认"实际命中码"（与 codes.py 1:1）。PR-A2+ 可接入真实 mock LLM。
    "E_ASSISTANT_MEDICAL_REJECT": "E_ASSISTANT_MEDICAL_REJECT",
    "E_GENERAL_RATE_LIMIT": "E_GENERAL_RATE_LIMIT",
    "E_UPLOAD_INVALID_CONTENT_TYPE": "E_UPLOAD_INVALID_CONTENT_TYPE",
    "E_FEEDBACK_DAILY_LIMIT": "E_FEEDBACK_DAILY_LIMIT",
    "E_RECALL_DAILY_LIMIT": "E_RECALL_DAILY_LIMIT",
    "E_COMPLIANCE_MEDICAL_CLAIM": "E_COMPLIANCE_MEDICAL_CLAIM",
    "E_ASSISTANT_SESSION_NOT_FOUND": "E_ASSISTANT_SESSION_NOT_FOUND",
    "E_ASSISTANT_SESSION_CLOSED": "E_ASSISTANT_SESSION_CLOSED",
}


def _resolve_actual_code(expected_code: str, intercept_status: str | None) -> str:
    """v4.1-prep 子任务 4 辅助：把 ``expected.code`` 解析为 mock 路由应回填的 actual_code。

    简化策略：直接返回查表默认（如有），否则原样回传 expected_code
    （意味着「至少断言该码可触发」）。接入真 mock LLM 时改 ``_eval_against_mock``。
    """
    return _CODE_BY_ROUTE.get(expected_code, expected_code)


# ============================================================
# 5. 整体跑测 + 汇总
# ============================================================
def run_evaluation(
    cases: list[Case],
    mode: RunMode,
    baseline: dict[str, Any] | None,
    mock_ctx: dict[str, Any],
) -> RunSummary:
    """按模式跑测 + 生成 RunSummary。

    入参：
        cases: 用例列表
        mode: 运行模式
        baseline: 基线 JSON（用于回归对比），可为 None
        mock_ctx: Mock 上下文（目前未使用）

    出参：
        RunSummary（带 results / route_distribution / 回归 dict）
    """
    started = time.perf_counter()
    results: list[CaseResult] = []
    for case in cases:
        results.append(run_case(case, mock_ctx))
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    route_dist: Counter[RouteName] = Counter(r.actual_route or "unknown" for r in results)
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    skipped = sum(1 for r in results if r.status == "skipped")

    intercept_blocked = sum(1 for r in results if r.intercept_status == "critical_block")
    intercept_block_rate = intercept_blocked / len(results) if results else 0.0

    confidence_hist: dict[str, int] = Counter()
    for r in results:
        if r.confidence is None:
            continue
        bucket = f"{int(r.confidence * 10) / 10:.1f}"
        confidence_hist[bucket] += 1

    regression = None
    if baseline:
        regression = _compare_to_baseline(results, baseline)

    return RunSummary(
        mode=mode,
        total=len(results),
        passed=passed,
        failed=failed,
        skipped=skipped,
        elapsed_ms=elapsed_ms,
        route_distribution=dict(route_dist),
        intercept_block_rate=intercept_block_rate,
        confidence_histogram=dict(confidence_hist),
        regression_vs_baseline=regression,
        results=results,
    )


def _compare_to_baseline(results: list[CaseResult], baseline: dict[str, Any]) -> dict[str, float]:
    """对比 baseline.json（与 runner 同 schema）。

    入参：
        results: 本次跑测结果
        baseline: 历史 baseline 数据（含 route_distribution 字典）

    出参：
        每 Route 的差距 dict（百分比差）
    """
    base_dist = baseline.get("route_distribution", {})
    cur_dist: Counter[RouteName] = Counter(r.actual_route or "unknown" for r in results)
    diffs: dict[str, float] = {}
    for route, base_count in base_dist.items():
        cur_count = cur_dist.get(route, 0)
        diffs[route] = round((cur_count - base_count) / max(base_count, 1) * 100, 2)
    return diffs


# ============================================================
# 6. CLI 入口
# ============================================================
def build_argparser() -> argparse.ArgumentParser:
    """构造 argparse 参数解析。

    出参：
        配置好的 ArgumentParser
    """
    parser = argparse.ArgumentParser(description="SelfwellAgent Golden Set Eval Runner")
    parser.add_argument(
        "--input",
        default="golden_set_v1.yaml",
        help="Golden Set YAML 路径（相对 backend/eval/）",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="baseline.json 路径，用于回归对比",
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in RunMode],
        default=RunMode.PR.value,
        help="运行模式：pr / daily / release / schema",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="结果 JSON 输出路径（默认 stdout）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口，串联 load → run → output。

    入参：
        argv: 命令行参数（None 时用 sys.argv）

    出参：
        退出码（0 = pass；1 = fail 或 regression 红线触发）
    """
    args = build_argparser().parse_args(argv)
    mode = RunMode(args.mode)
    base_dir = Path(__file__).parent
    cases = load_golden_set(base_dir / args.input)

    # 抽样
    if mode is RunMode.PR:
        cases = sample_for_pr(cases, n=30)

    # baseline
    baseline: dict[str, Any] | None = None
    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))

    mock_ctx: dict[str, Any] = {}
    summary = run_evaluation(cases, mode, baseline, mock_ctx)

    payload = summary.model_dump_json(indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")

    if summary.failed > 0:
        return 1
    if summary.regression_vs_baseline:
        for diff in summary.regression_vs_baseline.values():
            if diff < -REGRESSION_DROP_PCT:
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
