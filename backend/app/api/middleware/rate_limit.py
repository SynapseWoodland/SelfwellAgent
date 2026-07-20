"""RateLimit 中间件（Sprint 0 骨架）。

真源：``docs/architecture/error-codes.md`` §三（429 Retry-After 三档约定）
+ ``docs/architecture/mvp-tech-architecture.md`` §十。

约定：
1. 三档 Retry-After：
   - **精确秒数**：message_zh 含 ``{seconds}`` 占位符 → 必带 Retry-After
   - **粒度提示**：message_zh 含"明日 / 5 分钟 / 1 分钟" → 推荐带（向上取整为秒）
   - **无明确时长**：message_zh 为模糊"稍后重试" → 不带 Retry-After
2. 优先级：精确秒数 > 粒度 > 无时长
3. 落地：当前 MVP 使用 Redis-backed token bucket（令牌桶）；Sprint 0 落地内存版（单进程）
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from collections.abc import MutableMapping
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response


# ─────────────────────────────────────────────────────────────────────────────
# §一 Retry-After 三档决策（真源 error-codes.md §3）
# ─────────────────────────────────────────────────────────────────────────────
_RETRY_AFTER_PRECISE = re.compile(r"\{seconds\}")
_RETRY_AFTER_GRANULAR_SEC = re.compile(r"(\d+)\s*秒")
_RETRY_AFTER_GRANULAR_MIN = re.compile(r"(\d+)\s*分钟")
_RETRY_AFTER_GRANULAR_HOUR = re.compile(r"(\d+)\s*小时")
_RETRY_AFTER_GRANULAR_DAY = re.compile(r"明日|明天|次日")


def compute_retry_after_seconds(message_zh: str | None) -> int | None:
    """根据 message_zh 文案语义，返回 ``Retry-After`` 秒数；无明确时长返回 None。

    Args:
        message_zh: 业务错误的中文文案。

    Returns:
        None（不写 Retry-After 头）或正整数秒数。

    """
    if not message_zh:
        return None
    if _RETRY_AFTER_PRECISE.search(message_zh):
        # 默认保守值 60s；若调用方有更精确秒数可走【带上具体值】的版本（见 §2）
        return 60
    if m := _RETRY_AFTER_GRANULAR_SEC.search(message_zh):
        return int(m.group(1))
    if m := _RETRY_AFTER_GRANULAR_MIN.search(message_zh):
        return int(m.group(1)) * 60
    if m := _RETRY_AFTER_GRANULAR_HOUR.search(message_zh):
        return int(m.group(1)) * 3600
    if _RETRY_AFTER_GRANULAR_DAY.search(message_zh):
        return 24 * 3600
    return None


# ─────────────────────────────────────────────────────────────────────────────
# §二 Token Bucket（按 user_id_pseudo 配额）
# ─────────────────────────────────────────────────────────────────────────────
class _Bucket:
    __slots__ = ("last_refill_at", "tokens")

    def __init__(self, capacity: int) -> None:
        self.tokens = float(capacity)
        self.last_refill_at = time.monotonic()


class InMemoryRateLimiter:
    """Token bucket 限流器（内存版，MVP 单 worker）。"""

    def __init__(self, *, capacity: int = 60, refill_per_sec: float = 1.0) -> None:
        self._capacity = capacity
        self._refill_per_sec = refill_per_sec
        self._buckets: MutableMapping[str, _Bucket] = defaultdict(self._new_bucket)

    def _new_bucket(self) -> _Bucket:
        return _Bucket(capacity=self._capacity)

    def check(self, key: str, cost: int = 1) -> bool:
        """Try to consume ``cost`` tokens. Return True if allowed."""
        bucket = self._buckets[key]
        now = time.monotonic()
        elapsed = now - bucket.last_refill_at
        bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._refill_per_sec)
        bucket.last_refill_at = now
        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# §三 ASGI 中间件
# ─────────────────────────────────────────────────────────────────────────────
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit middleware (per-IP token bucket).

    Usage:
        >>> app.add_middleware(RateLimitMiddleware, capacity=120, refill_per_sec=2.0)
    """

    def __init__(
        self, app: object, *, capacity: int = 120, refill_per_sec: float = 2.0
    ) -> None:
        super().__init__(app)
        self._limiter = InMemoryRateLimiter(capacity=capacity, refill_per_sec=refill_per_sec)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        key = (request.client.host if request.client else "anon") or "anon"
        if not self._limiter.check(key):
            # 触发 E_GENERAL_RATE_LIMIT（message 模糊 → 不带 Retry-After）
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "E_GENERAL_RATE_LIMIT",
                        "message_zh": "请求过于频繁，请稍后重试",
                        "message_en": "Too many requests, please retry later",
                    }
                },
            )
        return await call_next(request)  # type: ignore[no-any-return, operator]


__all__ = [
    "InMemoryRateLimiter",
    "RateLimitMiddleware",
    "compute_retry_after_seconds",
]
