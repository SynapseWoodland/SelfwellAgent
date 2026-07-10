"""Per-user Redis 限流（Sprint A Step 1.6 + 行业对标 §4 决策 V4.1）。

真源：
- ``docs/plan/assistant-smart-analyze-vision-pipeline_4_feasibility-benchmarks.md``
  §4：业界主流是 **sliding window log**（Sorted Set + Lua 脚本原子操作）；
  ``slowapi`` 默认 fixed-window 在窗口边界会 2x 突发，是已知的算法缺陷。
- ``assistant-smart-analyze-vision-pipeline_3_gap-audit.md`` §5.4：InMemory 限流
  在多 uvicorn worker 部署下各持一份，单 user 可绕 4x 触发（V3 调研 XC-1/XC-2）。
- ``assistant-smart-analyze-vision-pipeline_4_cursor-exec-plan.md``
  Step 1.6：per-user Redis 限流（key 策略 ``ratelimit:{action}:{user_id}``）。

算法说明：
1. 用 Redis Sorted Set（``ZSET``）记录每次请求的 timestamp（ms）。
2. ``ZREMRANGEBYSCORE`` 清掉 window_ms 之前的旧记录；``ZCARD`` 拿到当前活跃数。
3. 如果小于 limit，``ZADD`` 当前时间戳；否则判定为超限。
4. 整个流程必须用 ``EVAL`` Lua 脚本（**原子**），否则多 worker 间存在 race。
   用 ``pipeline()`` 替代会被 worker 并发打穿（每个 round-trip 之间没有原子保证）。

为什么不选 slowapi：
- slowapi 默认 fixed-window（窗口边界 2x 突发已知缺陷）。
- 业务已有 redis 依赖（pyproject.toml:43），自研 30 行 Lua 即可。
- 库与 settings 整合要写多一层 adapter，不如直接基于 redis.asyncio。

抛出 ``RateLimitExceeded``（含 ``retry_after``），由 router 层包成 429 + Retry-After 头。
"""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from typing import Final

from redis.asyncio import Redis
from redis.exceptions import ResponseError  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────
# §一 错误码 + 异常类型
# ─────────────────────────────────────────────────────────────────────────
from app.errors.codes import E_ASSISTANT_RATE_LIMIT

logger = logging.getLogger(__name__)

# 错误码字符串常量化，避免硬编码 "E_..." 在 app/ 其它文件中出现
RATE_LIMIT_CODE: Final[str] = E_ASSISTANT_RATE_LIMIT


class RateLimitExceeded(Exception):
    """429 触发时抛出。带 ``retry_after_sec`` 供 Retry-After 头填充。

    Attributes:
        retry_after_sec: 距离下次允许的最短等待秒数（向上取整）。
        remaining: 当前 window 内剩余可用次数（>0 时不应抛出此异常）。
        action: 限流动作标签（``smart_analyze`` / ``chat`` 等）。
        key: 限流 key（``ratelimit:{action}:{user_id}``），用于调试日志。
    """

    def __init__(
        self,
        *,
        retry_after_sec: int,
        remaining: int,
        action: str,
        key: str,
        message_zh: str = "请求过于频繁，请稍后再试",
    ) -> None:
        super().__init__(message_zh)
        self.retry_after_sec = max(retry_after_sec, 1)
        self.remaining = remaining
        self.action = action
        self.key = key
        self.message_zh = message_zh
        self.code = RATE_LIMIT_CODE

    def __repr__(self) -> str:
        return (
            f"RateLimitExceeded(action={self.action!r}, "
            f"retry_after_sec={self.retry_after_sec}, remaining={self.remaining}, "
            f"key={self.key!r})"
        )


# ─────────────────────────────────────────────────────────────────────────
# §二 Lua 脚本（原子操作：清旧 → 计数 → add-or-deny → 续 TTL）
# ─────────────────────────────────────────────────────────────────────────
# KEYS[1]  : ratelimit key（"ratelimit:{action}:{user_id}"）
# ARGV[1]  : now_ms（当前毫秒时间戳，整数字符串）
# ARGV[2]  : window_ms（窗口长度毫秒，整数字符串）
# ARGV[3]  : limit（窗口内允许最大次数，整数字符串）
# ARGV[4]  : member（去重 member；用 now_ms + 随机 hex 防同 ms 碰撞）
# 返回： [allowed(0/1), remaining(int), oldest_in_window_ms, retry_after_ms]
#   - allowed: 1=允许, 0=超限
#   - remaining: 本次允许后剩余可用次数
#   - oldest_in_window_ms: window 内最旧一条记录的 ms；超限时用于算 retry_after_ms
#   - retry_after_ms: 本次应等多久（ms）直到 window 内最旧一条过期
SLIDING_WINDOW_LUA: Final[str] = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

-- 1. 清掉 window_ms 之前的旧记录
local cutoff = now_ms - window_ms
redis.call('ZREMRANGEBYSCORE', key, 0, cutoff)

-- 2. 当前活跃数
local count = redis.call('ZCARD', key)

if count < limit then
    -- 3a. 未超限：写入本次 + 续 TTL（多给 1s 防止边界）
    redis.call('ZADD', key, now_ms, member)
    redis.call('PEXPIRE', key, window_ms + 1000)
    local remaining = limit - count - 1
    return {1, remaining, 0, 0}
end

-- 3b. 超限：拿 window 内最旧一条，算出 retry_after_ms
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local oldest_ms = 0
if oldest[2] then
    oldest_ms = tonumber(oldest[2])
end
local retry_after_ms = (oldest_ms + window_ms) - now_ms
if retry_after_ms < 0 then retry_after_ms = 0 end
return {0, 0, oldest_ms, retry_after_ms}
"""


# ─────────────────────────────────────────────────────────────────────────
# §三 check_rate_limit 函数
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """限流判定结果（``check_rate_limit`` 返回值）。

    Attributes:
        allowed: 是否放行。
        remaining: window 内剩余可用次数；超限时为 0。
        retry_after_sec: 距离下次允许的最短秒数（向上取整；>=1）。
        count: 当前 window 内活跃计数（含本次新增；超限时不含）。
    """

    allowed: bool
    remaining: int
    retry_after_sec: int
    count: int


async def _check_rate_limit_lua(redis: Redis, key: str, now_ms: int, window_ms: int, limit: int, member: str) -> RateLimitDecision:
    """Lua 版 sliding window（Redis 生产路径）。"""
    raw = await redis.eval(
        SLIDING_WINDOW_LUA,
        1,  # numkeys
        key,  # KEYS[1]
        str(now_ms),  # ARGV[1]
        str(window_ms),  # ARGV[2]
        str(limit),  # ARGV[3]
        member,  # ARGV[4]
    )
    # raw = [allowed, remaining, oldest_ms, retry_after_ms]
    allowed = int(raw[0]) == 1
    remaining = int(raw[1])
    retry_after_ms = int(raw[3])

    if allowed:
        return RateLimitDecision(
            allowed=True,
            remaining=max(remaining, 0),
            retry_after_sec=0,
            count=limit - max(remaining, 0),
        )
    # 向上取整到秒，<=0 兜底为 1（防止 "Retry-After: 0" 这种无意义头）
    retry_after_sec = max((retry_after_ms + 999) // 1000, 1)
    return RateLimitDecision(
        allowed=False,
        remaining=0,
        retry_after_sec=retry_after_sec,
        count=limit,
    )


async def _check_rate_limit_python_fallback(
    redis: Redis, key: str, now_ms: int, window_ms: int, limit: int, member: str
) -> RateLimitDecision:
    """纯 Python sliding window fallback（fakeredis 等不支持 EVAL 的环境）。

    逻辑与 SLIDING_WINDOW_LUA 完全一致，但用 Redis Python 命令模拟。

    注意：此 fallback **非原子**，并发场景下 count 可能轻微漂移，
    仅用于测试/CI 环境；生产路径永远走 Lua 版。
    """
    oldest_bound = now_ms - window_ms
    await redis.zremrangebyscore(key, "-inf", str(oldest_bound))
    current_count = await redis.zcard(key)
    if current_count < limit:
        await redis.zadd(key, {member: now_ms})
        await redis.expire(key, max(window_ms // 1000 + 1, 1))
        return RateLimitDecision(
            allowed=True,
            remaining=limit - (current_count + 1),
            # 例：limit=3
            #   第1次: current=0 → remaining=2（slot 0,1,2 空2个）
            #   第2次: current=1 → remaining=1（slot 1,2 空1个）
            #   第3次: current=2 → remaining=0（仅剩 slot 2）
            # 第4次: current=3 不 < limit → 走超限分支
            retry_after_sec=0,
            count=current_count + 1,
        )
    oldest = await redis.zrange(key, 0, 0, withscores=True)
    oldest_ms = int(oldest[0][1]) if oldest else now_ms
    retry_after_ms = max(oldest_ms + window_ms - now_ms, 0)
    retry_after_sec = max((retry_after_ms + 999) // 1000, 1)
    return RateLimitDecision(
        allowed=False,
        remaining=0,
        retry_after_sec=retry_after_sec,
        count=limit,
    )


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_sec: int,
) -> RateLimitDecision:
    """Per-user sliding window log 限流（Lua 原子，Python fallback）。

    Args:
        redis: ``redis.asyncio.Redis`` 客户端（连接池单例，外部管理）。
        key: 限流 key，业务约定 ``ratelimit:{action}:{user_id}``（与 Step 1.6 强一致）。
        limit: window 内允许的最大次数（>0）。
        window_sec: 窗口长度（秒，>0）。

    Returns:
        ``RateLimitDecision`` —— 包含 ``allowed`` / ``remaining`` / ``retry_after_sec``。

    Raises:
        ValueError: ``limit`` 或 ``window_sec`` <= 0。
        redis.exceptions.RedisError: Redis 调用失败（透传，由 router 层决定兜底）。

    Example::

        decision = await check_rate_limit(redis, "ratelimit:chat:user-001", 30, 60)
        if not decision.allowed:
            raise RateLimitExceeded(
                retry_after_sec=decision.retry_after_sec,
                remaining=decision.remaining,
                action="chat",
                key="ratelimit:chat:user-001",
            )

    Notes:
        生产走 Lua 原子版；fakeredis 等不支持 EVAL 的环境自动 fallback 到纯 Python 版。
        详见 ``backend/tests/unit/core/test_ratelimit.py``。
    """
    if limit <= 0:
        raise ValueError(f"limit must be > 0, got {limit}")
    if window_sec <= 0:
        raise ValueError(f"window_sec must be > 0, got {window_sec}")

    now_ms = int(time.time() * 1000)
    window_ms = window_sec * 1000
    # member: now_ms + 12 chars random hex 防同 ms 并发碰撞
    # （Redis ZSET member 唯一，碰撞会导致 ZADD 不加新分）
    member = f"{now_ms}-{secrets.token_hex(6)}"

    # 优先走 Lua 原子版；fakeredis 等不支持 EVAL 时 fallback 纯 Python
    try:
        return await _check_rate_limit_lua(redis, key, now_ms, window_ms, limit, member)
    except Exception as exc:  # noqa: BLE001
        exc_msg = str(exc)
        if "unknown command" in exc_msg.lower() or "noscript" in exc_msg.lower():
            return await _check_rate_limit_python_fallback(
                redis, key, now_ms, window_ms, limit, member
            )
        raise


def raise_if_exceeded(decision: RateLimitDecision, *, action: str, key: str) -> None:
    """``check_rate_limit`` 之后用：放行则 noop；超限则抛 ``RateLimitExceeded``。"""
    if decision.allowed:
        return
    raise RateLimitExceeded(
        retry_after_sec=decision.retry_after_sec,
        remaining=decision.remaining,
        action=action,
        key=key,
    )


# ─────────────────────────────────────────────────────────────────────────
# §四 业务友好 helper（router 入口常用 key 策略）
# ─────────────────────────────────────────────────────────────────────────
def build_key(action: str, user_id: str, *, prefix: str = "ratelimit") -> str:
    """构造限流 key：``{prefix}:{action}:{user_id}``（V4 Step 1.6 强约定）。

    Args:
        action: 限流动作标签（``smart_analyze`` / ``chat`` / ``upload`` ...）。
        user_id: 业务侧 user_id（UUID / snowflake 字符串）。
        prefix: key 前缀（默认 ``ratelimit``）；测试可改以避免污染生产 key 空间。

    Returns:
        ``ratelimit:{action}:{user_id}`` 格式字符串。

    Notes:
        显式拒绝空 user_id，避免 ``ratelimit:smart_analyze:`` 这种匿名 key
        与共享公网 IP 风险（V3 §5.4 XC-1）。Caller 应在更上层兜底 "匿名 = 拒绝"。
    """
    if not action:
        raise ValueError("action must not be empty")
    if not user_id:
        raise ValueError("user_id must not be empty (use IP fallback + separate key)")
    return f"{prefix}:{action}:{user_id}"


__all__ = [
    "RateLimitExceeded",
    "RateLimitDecision",
    "SLIDING_WINDOW_LUA",
    "build_key",
    "check_rate_limit",
    "raise_if_exceeded",
]
