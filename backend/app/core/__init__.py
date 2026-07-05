"""app.core — Selfwell 后端核心库。

Sprint 0 落地：
- ``log``：loguru 工厂 + 3 合规审计事件接口
- ``trace``：TraceContextMiddleware + trace_id ContextVar
- ``errors``：ErrorSeverity 4 级 + SelfwellError 子类 + Result[T, E] + to_error_response
- ``result``：Result 糖（ok/err/safe）
- ``retry``：tenacity async retry / backoff 工具

所有业务模块从 ``app.core.errors`` 引用异常类型，禁止 ``raise HTTPException(...)`` 散落。
"""

from app.core.errors import (
    DEGRADED,
    PERMANENT,
    TRANSIENT,
    USER_ERROR,
    DegradedError,
    Err,
    ErrorSeverity,
    Ok,
    PermanentError,
    Result,
    SelfwellError,
    TransientError,
    UserInputError,
    match_result,
    severity_rank,
    to_error_response,
)
from app.core.log import (
    audit_medical_reject,
    audit_persona_state_switch,
    audit_safety_violation,
    logger,
    setup_logging,
)
from app.core.result import err as _result_err
from app.core.result import ok as _result_ok
from app.core.result import safe as _result_safe
from app.core.retry import async_retry, retry_decorator
from app.core.trace import (
    TraceContextMiddleware,
    current_request_id,
    current_trace_id,
    request_id_var,
    trace_id_var,
)

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
    "TraceContextMiddleware",
    "TransientError",
    "UserInputError",
    "_result_err",
    "_result_ok",
    "_result_safe",
    "async_retry",
    "audit_medical_reject",
    "audit_persona_state_switch",
    "audit_safety_violation",
    "current_request_id",
    "current_trace_id",
    "logger",
    "match_result",
    "request_id_var",
    "retry_decorator",
    "setup_logging",
    "severity_rank",
    "to_error_response",
    "trace_id_var",
]
