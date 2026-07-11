"""loguru 工厂 + 合规审计 3 事件接口（Sprint 0 骨架 · v2 配色版）。

真源：``docs/spec/facts-anchor.md`` §7 合规红线 §10.4 第 9 条 + ``docs/api/error-codes.md`` §九合规
+ ``docs/data/recall-forbidden-words.yaml`` + ``docs/data/ack-pool.yaml`` forbidden_tokens

风格真源：D:\\agent-project\\SemanticMind\\backend\\app\\core\\log.py

约定：
1. 唯一合法 import：``from app.core.log import logger``（禁止 ``from loguru import logger``）
2. 业务事件用 kwargs 字段（不让 f-string 进 message）；让 Loki/Prometheus 可聚合
3. trace_id / request_id 由 ``TraceContextMiddleware`` 注入 ContextVar，
   本文件的 ``_inject_request_context`` patcher 自动透出到 loguru ``record["extra"]``
4. PII 黑名单（email/phone/card_number/diagnosis）通过 ``_scrub_pii`` patcher 在 sink 层拦截脱敏
5. 合规审计 3 事件 **必须**打：``audit_safety_violation`` / ``audit_medical_reject`` /
   ``audit_persona_state_switch``（SPEC §10.4 第 9 条 / SPEC §2.4.4）

输出格式（与 SemanticMind 对齐）：
    <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> |
    <magenta>request_id - {extra[request_id]}</magenta> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> -
    <level>{message}</level>
"""

from __future__ import annotations

import logging
import re
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from loguru import logger as _loguru_logger

# ─────────────────────────────────────────────────────────────────────────────
# §〇 ContextVar 占位（避免 import 期与 app.core.trace 循环依赖）
# 启动期这两个还是 None，会在 patcher 里 fallback 到 "-"
# ─────────────────────────────────────────────────────────────────────────────
_request_id_placeholder: ContextVar[str | None] = ContextVar(
    "_request_id_placeholder", default=None
)


def _try_get_request_id() -> str:
    """优先从 app.core.trace 拿真实 request_id；拿不到就 fallback ``-``。"""
    try:
        from app.core.trace import current_request_id

        rid = current_request_id()
        if rid:
            return rid
    except Exception:
        pass
    return "-"


def _try_get_trace_id() -> str:
    """优先从 app.core.trace 拿真实 trace_id；拿不到就 fallback ``-``。"""
    try:
        from app.core.trace import current_trace_id

        tid = current_trace_id()
        if tid:
            return tid
    except Exception:
        pass
    return "-"


# ─────────────────────────────────────────────────────────────────────────────
# §一 PII 黑名单（字段名匹配 → 替换为 [EMAIL]/[PHONE]/[CARD]）
# 实际生产建议：改用 OpenTelemetry + OTLP exporter；此处先用 patcher 兜底
# ─────────────────────────────────────────────────────────────────────────────
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[PHONE]"),
    (re.compile(r"\d{16,19}"), "[CARD]"),
]


def _scrub_pii(record: Any) -> None:
    """Loguru Patcher：扫描 message 与 kwargs，过滤 PII。"""
    message = record.get("message", "")
    if isinstance(message, str):
        for pat, repl in _PII_PATTERNS:
            message = pat.sub(repl, message)
        record["message"] = message

    record_dict = dict(record)
    for key in ("email", "phone", "card_number", "diagnosis", "text_content", "mood_text"):
        value = record_dict.get(key)
        if isinstance(value, str):
            for pat, repl in _PII_PATTERNS:
                value = pat.sub(repl, value)
            record[key] = value


# ─────────────────────────────────────────────────────────────────────────────
# §二 inject_request_context：把 request_id / trace_id 注入 record["extra"]
# 与 SemanticMind 风格的 inject_request_id 对齐；额外补 trace_id
# ─────────────────────────────────────────────────────────────────────────────
def _inject_request_context(record: Any) -> None:
    """Patcher：把当前 async 上下文的 request_id / trace_id 注入到 loguru record。"""
    record["extra"]["request_id"] = _try_get_request_id()
    record["extra"]["trace_id"] = _try_get_trace_id()


# ─────────────────────────────────────────────────────────────────────────────
# §三 统一日志格式（与 SemanticMind 对齐）
# ─────────────────────────────────────────────────────────────────────────────
LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>request_id - {extra[request_id]}</magenta> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>\n{exception}"
)


# ─────────────────────────────────────────────────────────────────────────────
# §四 Intercept stdlib logging（uvicorn / sqlalchemy 默认走 stdlib）
# ─────────────────────────────────────────────────────────────────────────────
def _intercept_stdlib() -> None:
    logging.basicConfig(handlers=[logging.NullHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        lib = logging.getLogger(name)
        lib.handlers = [_InterceptHandler()]
        lib.propagate = False


class _InterceptHandler(logging.Handler):
    """loguru 官方推荐的 stdlib → loguru bridge。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        _loguru_logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


# ─────────────────────────────────────────────────────────────────────────────
# §五 setup_logging() 主入口（幂等）
# ─────────────────────────────────────────────────────────────────────────────
_LOGGING_CONFIGURED = False


def setup_logging(
    *,
    level: str = "INFO",
    console_enable: bool = True,
    file_enable: bool = False,
    file_path: str = "logs/app.log",
    file_rotation: str = "100 MB",
    file_retention: str = "14 days",
) -> None:
    """初始化 loguru（幂等；多次调用仅生效第一次）。

    Args:
        level: 全局日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
        console_enable: 是否输出到 stdout（默认 True）。
        file_enable: 是否输出到文件（默认 False；生产建议开）。
        file_path: 文件路径（相对 cwd 解析；生产建议绝对路径）。
        file_rotation: loguru rotation 表达式（默认 100 MB）。
        file_retention: loguru retention 表达式（默认 14 days）。

    Note:
        配置项当前为函数参数；后续要 Pydantic 化时把字段搬到
        ``app_config.logging.console.*`` / ``app_config.logging.file.*``
        段（参考 SemanticMind 的设计），不破坏调用方签名。

    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    _LOGGING_CONFIGURED = True

    # 重置 + patcher
    _loguru_logger.remove()
    _loguru_logger.configure(patcher=lambda rec: (_scrub_pii(rec), _inject_request_context(rec)))

    # 控制台 sink
    if console_enable:
        _loguru_logger.add(
            sys.stdout,
            format=LOG_FORMAT,
            level=level,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )

    # 文件 sink（参考 SemanticMind LOG-FIX(WinError 32) 注释）
    if file_enable:
        log_path = Path(file_path)
        if not log_path.is_absolute():
            log_path = Path.cwd() / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _loguru_logger.add(
            sink=log_path,
            format=LOG_FORMAT,
            level=level,
            rotation=file_rotation,
            retention=file_retention,
            encoding="utf-8",
            enqueue=True,  # 多进程 / uvicorn reload 进程安全
            catch=True,  # rotation/IO 异常不污染 stderr
            delay=True,
        )

    _intercept_stdlib()


# ─────────────────────────────────────────────────────────────────────────────
# §六 导出统一 logger（建议全项目用这一个）
# ─────────────────────────────────────────────────────────────────────────────
logger = _loguru_logger.opt(colors=False)


# ─────────────────────────────────────────────────────────────────────────────
# §七 上下文绑定工具（参考 SemanticMind get_logger / bind_conversation_context）
# ─────────────────────────────────────────────────────────────────────────────
def get_logger(name: str = "selfwell", **kwargs: Any) -> Any:
    """获取带 name + 自定义 kwargs 绑定的 logger。

    Example:
        >>> log = get_logger("wx_login", platform="wx_mp")
        >>> log.info("wx_login_attempt", openid=openid[:12])

    """
    return logger.bind(name=name, **kwargs)


def bind_request_context(
    *,
    conversation_id: str | None = None,
    run_id: str | None = None,
    user_id: str | None = None,
) -> Any:
    """绑定业务上下文到 logger（不影响 request_id/trace_id，由 patcher 注入）。"""
    return logger.bind(
        conversation_id=conversation_id,
        run_id=run_id,
        user_id=user_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# §八 合规审计 3 事件接口（SPEC §10.4 第 9 条 / SPEC §2.4.4）
# ─────────────────────────────────────────────────────────────────────────────
def audit_safety_violation(
    *,
    user_id_pseudo: str,
    category: str,
    content_hash: str,
    matched_tokens: list[str],
    severity_label: str = "high",
) -> None:
    """审计事件 1：内容安全违规（任意 safety/合规规则命中）。

    必传字段（与 ``audit_logger.json_schema`` 对齐）：
    - user_id_pseudo: 脱敏用户 ID（L1 §5.3）
    - category: 违规类别（medical/efficacy/appearance/numeric_judge 等）
    - content_hash: 内容 SHA256（用于回溯原始投诉，不存原内容）
    - matched_tokens: 命中的 token 列表（最多 10 个，超出截断）
    """
    logger.warning(
        "audit_safety_violation",
        user_id_pseudo=user_id_pseudo,
        category=category,
        content_hash=content_hash,
        matched_tokens=matched_tokens[:10],
        severity_label=severity_label,
    )


def audit_medical_reject(
    *,
    user_id_pseudo: str,
    reason: str,
    score: float,
    matched_keywords: list[str],
    session_id: str | None = None,
) -> None:
    """审计事件 2：医疗相关拒答（M5 SmartRouter / M2 ComplianceChecker 命中医疗词）。"""
    logger.warning(
        "audit_medical_reject",
        user_id_pseudo=user_id_pseudo,
        reason=reason,
        score=score,
        matched_keywords=matched_keywords[:10],
        session_id=session_id,
    )


def audit_persona_state_switch(
    *,
    user_id_pseudo: str,
    from_state: str,
    to_state: str,
    trigger: str,
    session_id: str | None = None,
    mock_reason: str | None = None,
) -> None:
    """审计事件 3：M5 Persona FSM 状态切换。

    状态机：``warm`` / ``neutral`` / ``slight_hug`` / ``medical_guarded``
    （见 ``docs/spec/facts-anchor.md`` §4 + ADR-0015）。

    Args:
        user_id_pseudo: 脱敏用户 ID。
        from_state: 切换前状态。
        to_state: 切换后状态。
        trigger: 触发原因（intent 或外部事件）。
        session_id: 可选会话 ID。
        mock_reason: 当回复走静态兜底（llm_model="static-fallback" / cost=0）
            时透出原因（例如 ``llm_unavailable`` / ``rule_engine_fallback``），
            便于运维聚合分析 mock 触发频率。

    """
    extra: dict[str, object] = {
        "from_state": from_state,
        "to_state": to_state,
        "trigger": trigger,
        "session_id": session_id,
    }
    if mock_reason is not None:
        extra["mock_reason"] = mock_reason
    logger.info("audit_persona_state_switch", user_id_pseudo=user_id_pseudo, **extra)


__all__ = [
    "LOG_FORMAT",
    "Path",  # re-export 以便测试里临时使用
    "audit_medical_reject",
    "audit_persona_state_switch",
    "audit_safety_violation",
    "bind_request_context",
    "get_logger",
    "logger",
    "setup_logging",
]
