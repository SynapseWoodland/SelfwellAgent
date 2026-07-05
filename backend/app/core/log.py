"""loguru 工厂 + 合规审计 3 事件接口（Sprint 0 骨架）。

真源：``docs/spec/facts-anchor.md`` §7 合规红线 §10.4 第 9 条 + ``docs/api/error-codes.md`` §九合规
+ ``docs/data/recall-forbidden-words.yaml`` + ``docs/data/ack-pool.yaml`` forbidden_tokens

约定：
1. 唯一合法 import：``from app.core.log import logger``（禁止 ``from loguru import logger``）
2. 业务事件用 kwargs 字段（不让 f-string 进 message）；让 Loki/Prometheus 可聚合
3. trace_id / request_id 由 ``TraceContextMiddleware`` 自动注入（无需手动 ``bind``）
4. PII 黑名单（email/phone/card_number/diagnosis）通过 ``Patcher`` 在 sink 层拦截脱敏
5. 合规审计 3 事件 **必须**打：``audit_safety_violation`` / ``audit_medical_reject`` /
   ``audit_persona_state_switch``（SPEC §10.4 第 9 条 / SPEC §2.4.4）
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger as _loguru_logger

# ─────────────────────────────────────────────────────────────────────────────
# §一 PII 黑名单（字段名匹配 → 替换为 ***REDACTED***）
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
# §二 Intercept stdlib logging（uvicorn / sqlalchemy 默认走 stdlib）
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
# §三 setup_logging() 主入口
# ─────────────────────────────────────────────────────────────────────────────
_LOGGING_CONFIGURED = False


def setup_logging(*, level: str = "INFO", json_sink: bool = True) -> None:
    """初始化 loguru。幂等；多次调用仅生效第一次。

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
        json_sink: 是否使用 JSON sink（默认 True，便于 Loki/ES 聚合）。

    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    _LOGGING_CONFIGURED = True

    _loguru_logger.remove()
    _loguru_logger.configure(patcher=_scrub_pii)

    if json_sink:
        _loguru_logger.add(
            sys.stdout,
            serialize=True,
            level=level,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )
    else:
        _loguru_logger.add(
            sys.stderr,
            level=level,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )

    _intercept_stdlib()


# ─────────────────────────────────────────────────────────────────────────────
# §四 导出统一 logger（建议全项目用这一个）
# ─────────────────────────────────────────────────────────────────────────────
logger = _loguru_logger.opt(colors=False)


# ─────────────────────────────────────────────────────────────────────────────
# §五 合规审计 3 事件接口（SPEC §10.4 第 9 条 / SPEC §2.4.4）
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
) -> None:
    """审计事件 3：M5 Persona FSM 状态切换。

    状态机：``warm`` / ``neutral`` / ``slight_hug`` / ``medical_guarded``
    （见 ``docs/spec/facts-anchor.md`` §4 + ADR-0015）。
    """
    logger.info(
        "audit_persona_state_switch",
        user_id_pseudo=user_id_pseudo,
        from_state=from_state,
        to_state=to_state,
        trigger=trigger,
        session_id=session_id,
    )


__all__ = [
    "Path",  # re-export 以便 ``from app.core.log import Path`` 在测试里临时使用
    "audit_medical_reject",
    "audit_persona_state_switch",
    "audit_safety_violation",
    "logger",
    "setup_logging",
]
