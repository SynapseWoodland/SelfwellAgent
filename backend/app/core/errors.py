"""业务错误层（Sprint 0 骨架）。

设计真源：``docs/architecture/error-codes.md`` + ``docs/spec/facts-anchor.md`` + ADR-0015。

该层职责：
1. ``ErrorSeverity``（4 级）内部异常分级，与 HTTP 业务码解耦
2. ``SelfwellError`` 域异常基类 + 典型子异常
3. ``Result[T, E]`` 类型用于 explicit-failure 路径
4. ``to_error_response`` 把 Python 异常 → 业务错误响应（与 openapi.yaml ErrorResponse 对齐）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable


# ─────────────────────────────────────────────────────────────────────────────
# §一 ErrorSeverity（4 级内部异常分级；与 HTTP 业务码解耦）
# ─────────────────────────────────────────────────────────────────────────────
ErrorSeverity = Literal["PERMANENT", "TRANSIENT", "USER_ERROR", "DEGRADED"]

PERMANENT: ErrorSeverity = "PERMANENT"
TRANSIENT: ErrorSeverity = "TRANSIENT"
USER_ERROR: ErrorSeverity = "USER_ERROR"
DEGRADED: ErrorSeverity = "DEGRADED"

_SEVERITY_PRIORITY: dict[ErrorSeverity, int] = {
    PERMANENT: 0,
    TRANSIENT: 1,
    USER_ERROR: 2,
    DEGRADED: 3,
}


def severity_rank(severity: ErrorSeverity) -> int:
    """返回 ``ErrorSeverity`` 的降级优先级（值越小越高）。"""
    return _SEVERITY_PRIORITY[severity]


# ─────────────────────────────────────────────────────────────────────────────
# §二 SelfwellError 基类与典型子异常
# ─────────────────────────────────────────────────────────────────────────────
class SelfwellError(Exception):
    """Selfwell 业务异常基类。

    Attributes:
        code: ``E_<MODULE>_<VERB_OR_NOUN>`` 字符串，与 ``app/errors/codes.py`` 常量 1:1。
        message_zh / message_en: 文案，可含 ``{field}`` ``{value}`` ``{limit}`` 等占位符。
        severity: ``ErrorSeverity`` 4 级之一。
        http_status: 与 ``error-codes.md`` 表对齐。

    """

    code: str = "E_GENERAL_INTERNAL_ERROR"
    message_zh: str = "服务端错误，请稍后重试"
    message_en: str = "Server error, please retry later"
    severity: ErrorSeverity = PERMANENT
    http_status: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        severity: ErrorSeverity | None = None,
        http_status: int | None = None,
        **context: object,
    ) -> None:
        super().__init__(message or self.message_zh)
        if code is not None:
            self.code = code
        if severity is not None:
            self.severity = severity
        if http_status is not None:
            self.http_status = http_status
        self.context: dict[str, object] = dict(context)

    def render_zh(self) -> str:
        """用 ``context`` 插值 message_zh 中的 ``{key}`` 占位符。"""
        try:
            return self.message_zh.format(**self.context)
        except (KeyError, IndexError):
            return self.message_zh

    def render_en(self) -> str:
        try:
            return self.message_en.format(**self.context)
        except (KeyError, IndexError):
            return self.message_en


class PermanentError(SelfwellError):
    """永久错误：不会因为重试而改变结果（如业务参数校验失败）。"""

    severity: ErrorSeverity = PERMANENT
    http_status: int = 400


class TransientError(SelfwellError):
    """临时错误：可能因重试成功（如 LLM 5xx、Redis 暂时不可用）。"""

    severity: ErrorSeverity = TRANSIENT
    http_status: int = 503


class UserInputError(SelfwellError):
    """用户输入错误：400 系列，4 级中最优先返回。"""

    severity: ErrorSeverity = USER_ERROR
    http_status: int = 400


class DegradedError(SelfwellError):
    """降级错误：系统通过降级策略返回（不影响主流程）。"""

    severity: ErrorSeverity = DEGRADED
    http_status: int = 200


# ─────────────────────────────────────────────────────────────────────────────
# §三 Result[T, E] 类型（Rust-inspired explicit-failure）
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(slots=True)
class Ok[T]:
    """Result[T, E] 的成功分支。"""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value


@dataclass(slots=True)
class Err[E]:
    """Result[T, E] 的失败分支。"""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> object:
        raise ValueError(f"called unwrap() on Err: {self.error!r}")

    def unwrap_or[U](self, default: U) -> U:
        return default


type Result[T, E] = Ok[T] | Err[E]  # PEP 695 alias


def match_result[T, E, R](
    result: Result[T, E],
    on_ok: Callable[[T], R],
    on_err: Callable[[E], R],
) -> R:
    """对 Result 进行 pattern match（CASE OF）。"""
    if isinstance(result, Ok):
        return on_ok(result.value)
    return on_err(result.error)


def to_error_response(exc: Exception) -> dict[str, dict[str, str]]:
    """Convert Python exception to ``{error: {code, message_zh, message_en}}`` shape.

    与 ``openapi.yaml#/components/schemas/ErrorResponse`` 100% 对齐。
    """
    if isinstance(exc, SelfwellError):
        return {
            "error": {
                "code": exc.code,
                "message_zh": exc.render_zh(),
                "message_en": exc.render_en(),
            }
        }
    return {
        "error": {
            "code": "E_GENERAL_INTERNAL_ERROR",
            "message_zh": "服务端错误，请稍后重试",
            "message_en": "Server error, please retry later",
        }
    }


__all__ = [
    "DEGRADED",
    "PERMANENT",
    "TRANSIENT",
    "USER_ERROR",
    "DegradedError",
    "Err",
    "ErrorSeverity",
    "Ok",
    "PermanentError",
    "Result",
    "SelfwellError",
    "TransientError",
    "UserInputError",
    "match_result",
    "severity_rank",
    "to_error_response",
]
