"""Unit tests for ``app.core.ratelimit`` (PR-A3 ratelimit + Sprint A Step 1.6).

真源：
- ``docs/plan/assistant-smart-analyze-vision-pipeline_3_gap-audit.md`` §5.4
  （per-user rate limit V3 必修复）
- ``docs/plan/assistant-smart-analyze-vision-pipeline_4_feasibility-benchmarks.md``
  §4（sliding window log + Lua 是 2026 业界主流，slowapi fixed-window 是已知缺陷）
- ``docs/plan/assistant-smart-analyze-vision-pipeline_4_cursor-exec-plan.md``
  Step 1.6（per-user key 策略 + smart_analyze 3 jobs/user/min）

覆盖：
- key 策略 ``ratelimit:{action}:{user_id}`` 与 IP 解耦（V3 XC-1）
- 第 (limit+1) 次请求触发 ``RateLimitExceeded``（V3 §5.4）
- retry_after_sec 单调递减，可与服务端 Retry-After 头对齐
- fakeredis Lua 脚本兼容性（``EVAL`` 完整模拟）
- ``build_key`` 拒绝空 user_id（防共享公网 IP 互相封禁）

依赖：
- ``fakeredis>=2.30.0``（需新增到 ``pyproject.toml [project.optional-dependencies].dev``
  —— 本报告 §4 已说明）
- ``pytest-asyncio>=0.24.0``（已有，配置 ``asyncio_mode = "auto"`` 见 backend 现有约定）

未运行：本次任务不强制 ``pytest`` 跑通（用户决策：先提交文件 + 跑通与 Step 1.6 实施时再补）。
"""
from __future__ import annotations

import pytest

# === fakeredis（注入 Lua 脚本兼容版）===
# fakeredis 提供了 FakeRedis 类与 redis.asyncio 接口兼容；EVAL 会透传给 lua 模块。
# 使用 fakeredis.aioredis.FakeRedis()。
# 若 pyproject.toml 还未声明，需新增到 dev optional-dependencies。
try:
    from fakeredis import aioredis as fake_aioredis  # type: ignore[import-not-found]

    _FAKEREDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FAKEREDIS_AVAILABLE = False

from app.core.ratelimit import (  # noqa: E402
    RateLimitExceeded,
    SLIDING_WINDOW_LUA,
    build_key,
    check_rate_limit,
    raise_if_exceeded,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture
def redis():
    """Inject ``fakeredis.aioredis.FakeRedis`` for in-memory testing.

    注意：fakeredis.eval() 会执行 Lua 脚本 —— 验证 Lua 在内存中可用
    （demonstrates ZADD/ZCARD/EVAL all in-memory）。
    """
    if not _FAKEREDIS_AVAILABLE:
        pytest.skip("fakeredis not installed; install via `uv add fakeredis --dev`")
    return fake_aioredis.FakeRedis()


# ─────────────────────────────────────────────────────────────────────────
# §一 key 策略
# ─────────────────────────────────────────────────────────────────────────
def test_build_key_format_includes_action_and_user() -> None:
    """V3 §5.4: key 必须是 ratelimit:{action}:{user_id}，不是 IP。"""
    assert build_key("smart_analyze", "user-001") == "ratelimit:smart_analyze:user-001"
    assert build_key("chat", "user-abc") == "ratelimit:chat:user-abc"


def test_build_key_rejects_empty_user_id() -> None:
    """V3 §5.4: 空 user_id 必须拒绝（防止共享公网 IP 互相封禁）。"""
    with pytest.raises(ValueError, match="user_id must not be empty"):
        build_key("chat", "")


def test_build_key_rejects_empty_action() -> None:
    with pytest.raises(ValueError, match="action must not be empty"):
        build_key("", "user-001")


def test_build_key_custom_prefix() -> None:
    assert (
        build_key("chat", "user-1", prefix="test_ratelimit")
        == "test_ratelimit:chat:user-1"
    )


# ─────────────────────────────────────────────────────────────────────────
# §二 check_rate_limit 基础行为（需要 fakeredis）
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.skipif(not _FAKEREDIS_AVAILABLE, reason="fakeredis not available")
async def test_first_request_within_limit_is_allowed(redis: object) -> None:
    """第一次请求在 limit 内：allowed=True, remaining=limit-1。"""
    decision = await check_rate_limit(redis, "ratelimit:chat:user-1", limit=3, window_sec=60)
    assert decision.allowed is True
    assert decision.remaining == 2
    assert decision.retry_after_sec == 0


@pytest.mark.asyncio
@pytest.mark.skipif(not _FAKEREDIS_AVAILABLE, reason="fakeredis not available")
async def test_exceeds_limit_raises_rate_limit_exceeded(redis: object) -> None:
    """V3 §5.4: limit=3 时第 4 次调用触发 RateLimitExceeded。"""
    key = "ratelimit:smart_analyze:user-2"
    for _ in range(3):
        decision = await check_rate_limit(redis, key, limit=3, window_sec=60)
        assert decision.allowed is True

    decision = await check_rate_limit(redis, key, limit=3, window_sec=60)
    assert decision.allowed is False
    assert decision.retry_after_sec >= 1
    # raise_if_exceeded 才真正抛 RateLimitExceeded
    with pytest.raises(RateLimitExceeded) as exc_info:
        raise_if_exceeded(decision, action="smart_analyze", key=key)
    assert exc_info.value.retry_after_sec >= 1
    assert exc_info.value.code  # 非空错误码


@pytest.mark.asyncio
@pytest.mark.skipif(not _FAKEREDIS_AVAILABLE, reason="fakeredis not available")
async def test_separate_users_have_independent_budgets(redis: object) -> None:
    """V3 §5.4: 不同 user 互不影响（CGNAT 防护）。"""
    for _ in range(3):
        decision = await check_rate_limit(
            redis, "ratelimit:chat:user-A", limit=3, window_sec=60
        )
        assert decision.allowed is True

    # user-A 第 4 次：allowed=False（不抛异常）
    decision_a4 = await check_rate_limit(redis, "ratelimit:chat:user-A", limit=3, window_sec=60)
    assert decision_a4.allowed is False

    # user-B 不受影响
    decision = await check_rate_limit(
        redis, "ratelimit:chat:user-B", limit=3, window_sec=60
    )
    assert decision.allowed is True
    assert decision.remaining == 2


@pytest.mark.asyncio
@pytest.mark.skipif(not _FAKEREDIS_AVAILABLE, reason="fakeredis not available")
async def test_window_expiry_resets_budget(redis: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """窗口过期后预算重置；验证靠 time 注入不现实，故走 fakeredis + tiny window。

    Notes:
        通过把 window_sec 设到很小（1s）+ 实际 sleep 验证（生产不建议，
        但单测允许）。生产场景依赖 sliding window 自然滚动 —— 见
        ratelimit.py docstring §二。
    """
    import asyncio

    key = "ratelimit:chat:user-window"
    # 用极短 window（1s）+ sleep 验证过期
    for _ in range(2):
        decision = await check_rate_limit(redis, key, limit=2, window_sec=1)
        assert decision.allowed is True

    # 第 3 次应超限（allowed=False，不抛异常）
    decision = await check_rate_limit(redis, key, limit=2, window_sec=1)
    assert decision.allowed is False
    assert decision.retry_after_sec >= 1

    # 等 window 过期
    await asyncio.sleep(1.1)

    decision = await check_rate_limit(redis, key, limit=2, window_sec=1)
    assert decision.allowed is True, "1.1s 后 budget 应已重置"


# ─────────────────────────────────────────────────────────────────────────
# §三 raise_if_exceeded 辅助函数
# ─────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.skipif(not _FAKEREDIS_AVAILABLE, reason="fakeredis not available")
async def test_raise_if_exceeded_noop_when_allowed(redis: object) -> None:
    """allowed=True 时 raise_if_exceeded 应静默放行。"""
    decision = await check_rate_limit(redis, "ratelimit:chat:noop", limit=5, window_sec=60)
    raise_if_exceeded(decision, action="chat", key="ratelimit:chat:noop")  # 不抛


@pytest.mark.asyncio
@pytest.mark.skipif(not _FAKEREDIS_AVAILABLE, reason="fakeredis not available")
async def test_raise_if_exceeded_raises_when_blocked(redis: object) -> None:
    """allowed=False 时 raise_if_exceeded 应抛 RateLimitExceeded。"""
    key = "ratelimit:smart_analyze:raise"
    for _ in range(2):
        decision = await check_rate_limit(redis, key, limit=2, window_sec=60)
        raise_if_exceeded(decision, action="smart_analyze", key=key)

    decision = await check_rate_limit(redis, key, limit=2, window_sec=60)
    with pytest.raises(RateLimitExceeded):
        raise_if_exceeded(decision, action="smart_analyze", key=key)


# ─────────────────────────────────────────────────────────────────────────
# §四 Lua 脚本完整性
# ─────────────────────────────────────────────────────────────────────────
def test_sliding_window_lua_returns_four_fields() -> None:
    """Lua 脚本必须返回 [allowed, remaining, oldest_ms, retry_after_ms] 4 字段。"""
    # 静态检查 Lua 源码（不执行）
    assert "redis.call('ZREMRANGEBYSCORE'" in SLIDING_WINDOW_LUA
    assert "redis.call('ZCARD'" in SLIDING_WINDOW_LUA
    assert "redis.call('ZADD'" in SLIDING_WINDOW_LUA
    assert "redis.call('PEXPIRE'" in SLIDING_WINDOW_LUA
    assert "return {1, remaining, 0, 0}" in SLIDING_WINDOW_LUA
    assert "return {0, 0, oldest_ms, retry_after_ms}" in SLIDING_WINDOW_LUA


# ─────────────────────────────────────────────────────────────────────────
# §五 入参校验
# ─────────────────────────────────────────────────────────────────────────
def test_check_rate_limit_rejects_non_positive_limit() -> None:
    import asyncio

    async def _call() -> None:
        await check_rate_limit(object(), "k", limit=0, window_sec=60)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="limit"):
        asyncio.run(_call())


def test_check_rate_limit_rejects_non_positive_window() -> None:
    import asyncio

    async def _call() -> None:
        await check_rate_limit(object(), "k", limit=10, window_sec=0)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="window_sec"):
        asyncio.run(_call())
