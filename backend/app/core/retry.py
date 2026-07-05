"""tenacity retry / backoff 工具（Sprint 0 骨架）。

真源：``docs/architecture/mvp-tech-architecture.md`` §十 §10.2 LLM 4 级降级链 +
``docs/spec/facts-anchor.md`` §9 LLM 配置。

约定：
1. 所有 LLM 调用必须走降级链（本文件仅做单层 retry；降级链见 ``llm/fallback_chain.py``）
2. 指数退避：``multiplier=2``，base 0.5s → 上限 8s（与 LLM API 友好）
3. 仅对 ``TransientError`` / ``httpx.TimeoutException`` / ``httpx.ConnectError`` /
   ``openai.APIConnectionError`` / ``anthropic.APIConnectionError`` 重试；
   ``PermanentError`` / ``UserInputError`` **绝不重试**
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.errors import TransientError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["async_retry", "retry_decorator"]


# ─────────────────────────────────────────────────────────────────────────────
# §一 可重试异常类型（白名单）
# ─────────────────────────────────────────────────────────────────────────────
def _is_retryable_exception(exc: BaseException) -> bool:
    """判断异常是否属于可重试白名单。

    允许重试的：
    - ``app.core.errors.TransientError``（域内自定义 5xx 重试入口）
    - ``httpx.TimeoutException`` / ``httpx.ConnectError``
    - ``openai.APIConnectionError`` / ``anthropic.APIConnectionError``
    - ``ConnectionError`` / ``TimeoutError``
    """
    if isinstance(exc, TransientError):
        return True
    name = type(exc).__name__
    module = type(exc).__module__
    # httpx
    if module.startswith("httpx") and name in {
        "TimeoutException",
        "ConnectError",
        "RemoteProtocolError",
    }:
        return True
    # openai / anthropic connection class
    if module.startswith(("openai", "anthropic")) and name.endswith("Error"):
        return "connection" in name.lower() or "timeout" in name.lower()
    return bool(isinstance(exc, (ConnectionError, TimeoutError, asyncio.TimeoutError)))


# ─────────────────────────────────────────────────────────────────────────────
# §二 内部回调：把 retry 事件打到日志（便于运维定位频繁重试）
# ─────────────────────────────────────────────────────────────────────────────
def _before_sleep_log(retry_state: RetryCallState) -> None:
    # Lazy import 避免 log.py 导入循环（log.py 不该依赖 retry.py）
    from app.core.log import logger

    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "retry_attempt",
        attempt=retry_state.attempt_number,
        next_sleep_sec=retry_state.next_action.sleep if retry_state.next_action else 0.0,
        exc_type=type(exc).__name__ if exc else None,
        exc_msg=str(exc)[:200] if exc else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# §三 async_retry(fn, *, attempts=4) → 可重试装饰器
# ─────────────────────────────────────────────────────────────────────────────
def async_retry(
    *,
    attempts: int = 4,
    min_seconds: float = 0.5,
    max_seconds: float = 8.0,
    multiplier: float = 2.0,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """构造异步重试装饰器。

    Args:
        attempts: 最大尝试次数（含首次调用，默认 4）。
        min_seconds: 初始退避秒数。
        max_seconds: 最大退避秒数。
        multiplier: 退避乘子。

    Example:
        >>> @async_retry(attempts=3)
        ... async def call_llm() -> str:
        ...     return await openai_client.chat("hello")

    """

    def decorator(
        fn: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        retryer = AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=multiplier, min=min_seconds, max=max_seconds),
            retry=retry_if_exception_type(Exception),  # 兜底；真实判断在 fn 内
            reraise=True,
            before_sleep=_before_sleep_log,
        )

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            async for attempt in retryer:
                with attempt:
                    try:
                        return await fn(*args, **kwargs)
                    except Exception as exc:
                        if not _is_retryable_exception(exc):
                            raise
                        last_exc = exc
                        raise
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("unreachable: retry exhausted without exception")

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# §四 兼容旧的命名（向后兼容 + 测试 import 用）
# ─────────────────────────────────────────────────────────────────────────────
retry_decorator = async_retry
