"""Unit tests for ``app.core.job_state`` (PR-A1).

真源：``docs/design/mvp_a_场景端到端实现方案_d1d163fa`` §5.1 + §6.1。

覆盖：
- create + get_status
- update_status 生命周期（queued → running → ready）
- append_event + next_event 顺序消费
- next_event 阻塞 + 事件唤醒
- next_event timeout → None
- close_job 清空 state（next_event 立即返回 None）
- TTL 30min 过期（注入 fake clock）
- create_job 校验（空 report_id / 空 user_id）
- update_status 校验（不存在的 job_id）
- append_event 校验（非法 kind）
- get_status 跨 user 越权返回 None
- module-level get_job_state_store / reset_job_state_store
"""
from __future__ import annotations

import asyncio

import pytest

from app.core.job_state import (
    DEFAULT_JOB_TTL_SECONDS,
    InMemoryJobStateStore,
    JobEvent,
    JobStateError,
    JobStateStore,
    get_job_state_store,
    reset_job_state_store,
)


# ─────────────────────────────────────────────────────────────────────────────
# §一 helpers
# ─────────────────────────────────────────────────────────────────────────────
class _FakeClock:
    """可手动推进的 fake 时钟（替身 ``time.monotonic``）。

    用法：
        clock = _FakeClock()
        store = InMemoryJobStateStore(clock=clock.monotonic)
        # 推进 1 小时：
        clock.advance(3600)
    """

    def __init__(self, start: float = 1000.0) -> None:
        self._now: float = start

    def monotonic(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def _make_store(*, clock: _FakeClock | None = None) -> InMemoryJobStateStore:
    # 显式没传 clock 时用 InMemoryJobStateStore 的默认（time.monotonic）
    if clock is None:
        return InMemoryJobStateStore()
    return InMemoryJobStateStore(clock=clock.monotonic)


# ─────────────────────────────────────────────────────────────────────────────
# §二 create / get_status
# ─────────────────────────────────────────────────────────────────────────────
def test_create_and_get_status() -> None:
    """create_job 返回 UUID4；get_status 默认 'queued'。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    assert isinstance(job_id, str)
    assert len(job_id) == 36  # UUID4 字符串长度
    assert store.get_status(job_id, user_id="u-1") == "queued"


def test_get_status_returns_none_for_unknown_job() -> None:
    """未知 job_id → None。"""
    store = _make_store()
    assert store.get_status("not-a-real-uuid", user_id="u-1") is None


def test_get_status_returns_none_for_other_user() -> None:
    """跨 user 访问 → None（防越权）。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    assert store.get_status(job_id, user_id="u-2") is None
    # 原始 user 仍可访问
    assert store.get_status(job_id, user_id="u-1") == "queued"


def test_create_job_rejects_empty_inputs() -> None:
    """空 report_id / user_id → JobStateError。"""
    store = _make_store()
    with pytest.raises(JobStateError) as exc_info:
        store.create_job(report_id="", user_id="u-1")
    assert exc_info.value.code == "E_JOB_INVALID_INPUT"

    with pytest.raises(JobStateError):
        store.create_job(report_id="r-1", user_id="")


# ─────────────────────────────────────────────────────────────────────────────
# §三 update_status 生命周期
# ─────────────────────────────────────────────────────────────────────────────
def test_update_status_lifecycle() -> None:
    """Queued → running → ready 状态机迁移。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")

    assert store.get_status(job_id, user_id="u-1") == "queued"
    store.update_status(job_id, "running")
    assert store.get_status(job_id, user_id="u-1") == "running"
    store.update_status(job_id, "ready", payload={"report_id": "r-1"})
    assert store.get_status(job_id, user_id="u-1") == "ready"


def test_update_status_unknown_job_raises() -> None:
    """更新不存在的 job → JobStateError。"""
    store = _make_store()
    with pytest.raises(JobStateError) as exc_info:
        store.update_status("not-a-real-uuid", "running")
    assert exc_info.value.code == "E_JOB_NOT_FOUND"


def test_update_status_empty_inputs_raise() -> None:
    """空 job_id / status → JobStateError。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    with pytest.raises(JobStateError):
        store.update_status("", "running")
    with pytest.raises(JobStateError):
        store.update_status(job_id, "")


# ─────────────────────────────────────────────────────────────────────────────
# §四 append_event + next_event
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_append_and_next_event_returns_in_order() -> None:
    """多事件按 append 顺序消费。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")

    store.append_event(job_id, {"kind": "stage", "stage": "preprocess", "percent": 15})
    store.append_event(job_id, {"kind": "stage", "stage": "analyzing", "percent": 45})
    store.append_event(job_id, {"kind": "done", "report_id": "r-1"})

    evt1 = await store.next_event(job_id, timeout=1.0)
    assert evt1 is not None
    assert evt1.kind == "stage"
    assert evt1.payload == {"stage": "preprocess", "percent": 15}

    evt2 = await store.next_event(job_id, timeout=1.0)
    assert evt2 is not None
    assert evt2.kind == "stage"
    assert evt2.payload == {"stage": "analyzing", "percent": 45}

    evt3 = await store.next_event(job_id, timeout=1.0)
    assert evt3 is not None
    assert evt3.kind == "done"
    assert evt3.payload == {"report_id": "r-1"}


@pytest.mark.asyncio
async def test_next_event_blocks_then_resolves_on_event() -> None:
    """无事件时 next_event 阻塞；append_event 后立即返回。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")

    async def _producer() -> None:
        await asyncio.sleep(0.05)  # 50ms 后再推事件
        store.append_event(job_id, {"kind": "stage", "stage": "preprocess"})

    _producer_task = asyncio.create_task(_producer())
    # 让 producer task 在测试结束前不报错
    _producer_task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

    start = asyncio.get_event_loop().time()
    evt = await store.next_event(job_id, timeout=2.0)
    elapsed = asyncio.get_event_loop().time() - start

    assert evt is not None
    assert evt.kind == "stage"
    # 应被 producer 唤醒（≤ 1s），不是 timeout
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_next_event_returns_none_on_timeout() -> None:
    """无事件 + 短 timeout → 返回 None。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")

    evt = await store.next_event(job_id, timeout=0.1)
    assert evt is None


@pytest.mark.asyncio
async def test_next_event_returns_none_for_unknown_job() -> None:
    """未知 job_id → None。"""
    store = _make_store()
    evt = await store.next_event("not-a-real-uuid", timeout=0.1)
    assert evt is None


def test_append_event_validates_kind() -> None:
    """非法 event kind → JobStateError。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    with pytest.raises(JobStateError) as exc_info:
        store.append_event(job_id, {"kind": "nonsense"})
    assert exc_info.value.code == "E_JOB_INVALID_INPUT"


def test_append_event_validates_dict() -> None:
    """Event 不是 dict → JobStateError。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    with pytest.raises(JobStateError):
        store.append_event(job_id, "not-a-dict")  # type: ignore[arg-type]


def test_append_event_after_close_raises() -> None:
    """Close 后的 job 不能再 append_event（close_job 把 entry 从 dict 移除 → 报 NOT_FOUND）。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    store.close_job(job_id)
    # close_job 把 entry 从 self._jobs 中 pop 掉，所以 append_event 会拿到 NOT_FOUND
    # （业务上对调用方等价：job 不再可用）
    with pytest.raises(JobStateError) as exc_info:
        store.append_event(job_id, {"kind": "stage", "stage": "x"})
    assert exc_info.value.code == "E_JOB_NOT_FOUND"


def test_update_status_after_close_raises_not_found() -> None:
    """Close 后的 job 不能再 update_status（同样报 NOT_FOUND）。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    store.close_job(job_id)
    with pytest.raises(JobStateError) as exc_info:
        store.update_status(job_id, "running")
    assert exc_info.value.code == "E_JOB_NOT_FOUND"


# ─────────────────────────────────────────────────────────────────────────────
# §五 close_job
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_close_job_clears_state() -> None:
    """close_job → get_status 返回 None；next_event 立即返回 None。"""
    store = _make_store()
    job_id = store.create_job(report_id="r-1", user_id="u-1")
    store.update_status(job_id, "running")

    store.close_job(job_id)

    assert store.get_status(job_id, user_id="u-1") is None
    evt = await store.next_event(job_id, timeout=0.5)
    assert evt is None


def test_close_unknown_job_is_noop() -> None:
    """Close 不存在的 job 静默忽略（便于 shutdown / 测试清理）。"""
    store = _make_store()
    store.close_job("not-a-real-uuid")  # 不抛
    store.close_job("")  # 不抛


def test_close_all_clears_everything() -> None:
    """close_all 把所有 job 都关闭。"""
    store = _make_store()
    jid_1 = store.create_job(report_id="r-1", user_id="u-1")
    jid_2 = store.create_job(report_id="r-2", user_id="u-1")
    store.close_all()
    assert store.get_status(jid_1, user_id="u-1") is None
    assert store.get_status(jid_2, user_id="u-1") is None


# ─────────────────────────────────────────────────────────────────────────────
# §六 TTL 过期
# ─────────────────────────────────────────────────────────────────────────────
def test_ttl_evicts_after_30min() -> None:
    """推进 fake clock 超过 TTL → job 被自动清理。"""
    clock = _FakeClock(start=0.0)
    store = InMemoryJobStateStore(clock=clock.monotonic, ttl_seconds=DEFAULT_JOB_TTL_SECONDS)
    job_id = store.create_job(report_id="r-1", user_id="u-1")

    # 不调 get_status（避免 touch）—— 直接推进时钟到 30min + 1s
    clock.advance(DEFAULT_JOB_TTL_SECONDS + 1.0)
    # 下一次 access 触发 lazy eviction
    assert store.get_status(job_id, user_id="u-1") is None


def test_ttl_refreshed_on_access() -> None:
    """get_status 会刷新 last_access_at，阻止过期。"""
    clock = _FakeClock(start=0.0)
    store = InMemoryJobStateStore(clock=clock.monotonic, ttl_seconds=60.0)
    job_id = store.create_job(report_id="r-1", user_id="u-1")

    # 推进 30s 并 access（refresh）—— 上次 access 是 0.0 → 30s 前，但 ≤ TTL=60s
    clock.advance(30.0)
    assert store.get_status(job_id, user_id="u-1") == "queued"
    # 这次 access 把 last_access_at refresh 到 30.0

    # 再推进 30s（总 60s，刚好 TTL）—— 上次 access 是 30.0，差 30s < 60s → 不过期
    clock.advance(30.0)
    assert store.get_status(job_id, user_id="u-1") == "queued"
    # 这次 access 把 last_access_at refresh 到 60.0

    # 再推进 61s（上次 access 61s 前）→ 超过 TTL 60s → 过期
    clock.advance(61.0)
    assert store.get_status(job_id, user_id="u-1") is None


# ─────────────────────────────────────────────────────────────────────────────
# §七 module-level singleton
# ─────────────────────────────────────────────────────────────────────────────
def test_module_singleton_lazy_init() -> None:
    """首次调 get_job_state_store() 才创建；reset 后下一次再创建新实例。"""
    reset_job_state_store()
    s1 = get_job_state_store()
    s2 = get_job_state_store()
    # singleton 模式：两次返回同一实例
    assert s1 is s2
    # 类型正确
    assert isinstance(s1, JobStateStore)
    assert isinstance(s1, InMemoryJobStateStore)
    reset_job_state_store()
    s3 = get_job_state_store()
    # reset 后是新实例
    assert s3 is not s1


# ─────────────────────────────────────────────────────────────────────────────
# §八 JobEvent dataclass
# ─────────────────────────────────────────────────────────────────────────────
def test_job_event_dataclass() -> None:
    """JobEvent 是 frozen dataclass；默认 payload 为空 dict。"""
    evt = JobEvent(kind="stage")
    assert evt.kind == "stage"
    assert evt.payload == {}

    evt2 = JobEvent(kind="done", payload={"report_id": "r-1"})
    assert evt2.payload == {"report_id": "r-1"}

    # frozen —— 改属性会抛 FrozenInstanceError
    with pytest.raises((AttributeError, Exception)):  # AttributeError / FrozenInstanceError 都接受
        evt.kind = "error"  # type: ignore[misc]
