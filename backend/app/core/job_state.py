"""In-process job state store for SSE / async pipeline 进度分发。

真源：``docs/design/mvp_a_场景端到端实现方案_d1d163fa`` §5.1 PR-A1 + §6.1。
- PR-A1 范围：只实现抽象 + 内存版 + 30min TTL + 与 ``app.state.job_state`` 集成。
- PR-A2 会基于本接口在 diagnosis router 里接真 pipeline；本期 **不** 实现 Redis 适配。

设计要点：
1. ``JobStateStore`` 是抽象基类 —— 多 worker 部署时可换 Redis pub/sub 实现，调用方零改动。
2. ``InMemoryJobStateStore`` 用 ``asyncio.Queue``（per-job 缓冲）+ ``asyncio.Event``（唤醒等待者）。
3. 30 分钟 TTL 懒清理（access 时 evict）；不启 background task，避免 uvicorn reload 时残留孤儿协程。
4. 全部依赖 ``asyncio`` / ``dataclasses`` / ``time`` / ``uuid``（stdlib），不引入新依赖。

约定：
- ``create_job`` 返回 ``job_id``（UUID4 字符串）；同时记录 ``report_id`` + ``user_id`` 绑定。
- ``update_status`` 状态机：``queued`` → ``running`` → ``ready`` / ``failed``（自由迁移，不强制）。
- ``append_event`` 把阶段事件（``stage``/``done``/``error``）推入 per-job queue。
- ``next_event`` 阻塞等待直到有事件或 timeout；timeout 时返回 ``None``，调用方应发 keepalive。
- ``close_job`` 清空 state，``next_event`` 之后会立即抛 ``JobStateError``（用于 stop streaming）。
"""
from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# 30 分钟 TTL —— 与 SSE 客户端最长存活时长对齐（前端 keepalive ≤ 30s；30min 够 retry + 慢 LLM）
DEFAULT_JOB_TTL_SECONDS: float = 30.0 * 60.0
# 内部 ``next_event`` 超时上限 —— SSE keepalive 间隔（10s）比这个短就行
DEFAULT_NEXT_EVENT_TIMEOUT_SECONDS: float = 10.0

# Report.status enum（与 plan §4.4 对齐）；不在此强制 —— 调用方可传其它字符串以便未来扩展
VALID_STATUSES: frozenset[str] = frozenset({"queued", "running", "ready", "failed"})


# ─────────────────────────────────────────────────────────────────────────────
# §一 事件 / 状态 dataclass
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(slots=True, frozen=True)
class JobEvent:
    """Per-job 事件 payload（推入 ``JobStateStore`` 后由消费者 ``next_event`` 弹出）。

    Attributes:
        kind: 事件类型 —— ``"stage"``（中间进度）/ ``"done"``（pipeline 收尾成功）/
            ``"error"``（pipeline 失败 / 超时）。
        payload: 透传 dict —— ``stage`` 含 ``{stage, percent, message}``；``done`` 含
            ``{report_id}``；``error`` 含 ``{code, message_zh, ...}``。

    """

    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _JobEntry:
    """内存中每个 job 的内部 state（不导出）。"""

    job_id: str
    report_id: str
    user_id: str
    status: str
    created_at: float
    last_access_at: float
    queue: asyncio.Queue[JobEvent] = field(default_factory=asyncio.Queue)
    event: asyncio.Event = field(default_factory=asyncio.Event)
    is_closed: bool = False
    last_payload: dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# §二 异常
# ─────────────────────────────────────────────────────────────────────────────
class JobStateError(Exception):
    """Job state 内部错误（不导出到业务码 —— 业务层应 catch 后转 ``SelfwellError``）。"""

    def __init__(self, code: str, message: str, **context: object) -> None:
        super().__init__(message)
        self.code = code
        self.context: dict[str, object] = dict(context)


# ─────────────────────────────────────────────────────────────────────────────
# §三 抽象基类
# ─────────────────────────────────────────────────────────────────────────────
class JobStateStore(ABC):
    """Job 状态 + 事件分发 抽象。

    适用场景：诊断 / 报告生成 pipeline 的 SSE 进度推送。设计参考 SemanticMind
    的 ``AppJobState``（event + queue），但本接口是 sync-friendly 的 dataclass，
    便于 PR-A2 的 router 直接 yield。
    """

    @abstractmethod
    def create_job(self, report_id: str, user_id: str) -> str:
        """创建新 job 并返回 ``job_id``。"""

    @abstractmethod
    def get_status(self, job_id: str, user_id: str) -> str | None:
        """查询 job 当前 status；不存在或不属于该 user → ``None``。"""

    @abstractmethod
    def update_status(
        self,
        job_id: str,
        status: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """更新 job 状态（带 TTL refresh）。"""

    @abstractmethod
    def append_event(self, job_id: str, event: dict[str, Any]) -> None:
        """追加一个 stage 事件（kind="stage" 包装为 ``JobEvent`` 入队）。"""

    @abstractmethod
    async def next_event(
        self,
        job_id: str,
        timeout: float = DEFAULT_NEXT_EVENT_TIMEOUT_SECONDS,
    ) -> JobEvent | None:
        """阻塞等待下一个事件；timeout 或 job 关闭时返回 ``None``。"""

    @abstractmethod
    def close_job(self, job_id: str) -> None:
        """关闭 job：标记 is_closed，唤醒所有等待的 ``next_event`` 返回 ``None``。"""

    def close_all(self) -> None:
        """关闭所有 job（lifespan shutdown 用；默认实现遍历 ``close_job``）。

        注意：本方法在抽象基类有默认实现；子类一般不需要 override。
        """
        # 默认实现：拿到内部 _jobs 字典的 keys，然后逐个 close
        # 子类（如 Redis 版）应 override 提供更高效实现
        internal_jobs = getattr(self, "_jobs", None)
        if isinstance(internal_jobs, dict):
            for jid in list(internal_jobs.keys()):
                self.close_job(jid)


# ─────────────────────────────────────────────────────────────────────────────
# §四 内存实现
# ─────────────────────────────────────────────────────────────────────────────
class InMemoryJobStateStore(JobStateStore):
    """``JobStateStore`` 的内存实现（asyncio.Queue + asyncio.Event）。

    Args:
        ttl_seconds: job 多久未被 access 后算过期（默认 30min）。
        clock: 可注入的时钟工厂（默认 ``time.monotonic``），便于测试 fake 时钟。
        next_event_timeout: ``next_event`` 默认 timeout。

    Note:
        全部方法对 asyncio loop 安全（asyncio 单线程模型）；不需额外 lock。
        多 worker 部署需换 Redis 适配（接口稳定，实现可替换）。

    """

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_JOB_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        next_event_timeout: float = DEFAULT_NEXT_EVENT_TIMEOUT_SECONDS,
    ) -> None:
        self._jobs: dict[str, _JobEntry] = {}
        self._ttl_seconds: float = ttl_seconds
        self._clock: Callable[[], float] = clock
        self._next_event_timeout: float = next_event_timeout

    # ── TTL 懒清理 ──────────────────────────────────────────────────────────
    def _evict_expired(self, now: float) -> None:
        """删除超过 TTL 未访问的 job（access 路径触发，非 background）。"""
        expired: list[str] = []
        for jid, entry in self._jobs.items():
            if now - entry.last_access_at > self._ttl_seconds:
                expired.append(jid)
        for jid in expired:
            entry = self._jobs.pop(jid, None)
            if entry is not None:
                entry.is_closed = True
                # 唤醒所有等待者（它们会看到 is_closed 后返回 None）
                entry.event.set()

    def _touch(self, entry: _JobEntry, now: float) -> None:
        entry.last_access_at = now

    # ── 公开 API ────────────────────────────────────────────────────────────
    def create_job(self, report_id: str, user_id: str) -> str:
        """创建新 job（状态 ``queued``），返回 ``job_id``（UUID4）。"""
        if not report_id:
            raise JobStateError("E_JOB_INVALID_INPUT", "report_id is required")
        if not user_id:
            raise JobStateError("E_JOB_INVALID_INPUT", "user_id is required")
        now = self._clock()
        self._evict_expired(now)
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = _JobEntry(
            job_id=job_id,
            report_id=report_id,
            user_id=user_id,
            status="queued",
            created_at=now,
            last_access_at=now,
        )
        return job_id

    def get_status(self, job_id: str, user_id: str) -> str | None:
        """查询 status；job 不存在 / user_id 不匹配 / 已关闭 → ``None``。"""
        now = self._clock()
        self._evict_expired(now)
        entry = self._jobs.get(job_id)
        if entry is None or entry.is_closed:
            return None
        if entry.user_id != user_id:
            # 跨 user 访问当 ``None`` —— 防越权（与 plan §6.1 一致）
            return None
        self._touch(entry, now)
        return entry.status

    def update_status(
        self,
        job_id: str,
        status: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """更新 status（不验证 status 字符串 —— 调用方负责）。

        Note:
            不在 ``update_status`` 内强制状态机迁移（业务侧可任意切换，例如
            ``ready`` → ``failed`` 重试场景）。PR-A2 路由侧会用 ``VALID_STATUSES``
            校验入参。

        """
        if not job_id:
            raise JobStateError("E_JOB_INVALID_INPUT", "job_id is required")
        if not status:
            raise JobStateError("E_JOB_INVALID_INPUT", "status is required")
        now = self._clock()
        self._evict_expired(now)
        entry = self._jobs.get(job_id)
        if entry is None:
            raise JobStateError("E_JOB_NOT_FOUND", f"job {job_id} not found")
        if entry.is_closed:
            raise JobStateError("E_JOB_CLOSED", f"job {job_id} is closed")
        entry.status = status
        if payload is not None:
            entry.last_payload = dict(payload)
        self._touch(entry, now)

    def append_event(self, job_id: str, event: dict[str, Any]) -> None:
        """追加一个 stage 事件（``kind`` 字段决定事件类型）。

        Args:
            job_id: 目标 job 的 UUID。
            event: 至少含 ``kind`` key（``stage``/``done``/``error``）；其它字段
                透传到 ``JobEvent.payload``。

        """
        if not job_id:
            raise JobStateError("E_JOB_INVALID_INPUT", "job_id is required")
        if not isinstance(event, dict):
            raise JobStateError("E_JOB_INVALID_INPUT", "event must be a dict")
        kind = str(event.get("kind", "stage"))
        if kind not in {"stage", "done", "error"}:
            raise JobStateError(
                "E_JOB_INVALID_INPUT",
                f"event kind must be one of stage/done/error, got {kind!r}",
            )
        payload = {k: v for k, v in event.items() if k != "kind"}
        now = self._clock()
        self._evict_expired(now)
        entry = self._jobs.get(job_id)
        if entry is None:
            raise JobStateError("E_JOB_NOT_FOUND", f"job {job_id} not found")
        if entry.is_closed:
            raise JobStateError("E_JOB_CLOSED", f"job {job_id} is closed")
        # asyncio.Queue 是线程/任务安全的（asyncio 单线程 + 内部 lock）
        entry.queue.put_nowait(JobEvent(kind=kind, payload=payload))
        entry.event.set()
        self._touch(entry, now)

    async def next_event(
        self,
        job_id: str,
        timeout: float = DEFAULT_NEXT_EVENT_TIMEOUT_SECONDS,
    ) -> JobEvent | None:
        """阻塞等待下一个 ``JobEvent``；timeout 或 job 关闭时返回 ``None``。

        实现：
        1. 先 ``Queue.get_nowait()`` 把已经到达的事件立刻返回（避免无谓 wait）。
        2. 否则 ``await asyncio.wait_for(event.wait(), timeout=timeout)``，等待唤醒。
        3. 唤醒后再 ``Queue.get_nowait()`` 拿事件；如 ``event.wait`` 实际是 timeout
           或 close 唤醒 → 队列可能为空 → 返回 ``None``。

        不用 ``asyncio.wait_for(queue.get())`` 的原因：Queue.get 无 ``Event`` 通知，
        必须依赖 producer 的 ``put`` —— 但本次实现里 producer 会在 put 后 ``event.set()``，
        用 event.wait 更直接（且能响应 close）。
        """
        if not job_id:
            raise JobStateError("E_JOB_INVALID_INPUT", "job_id is required")
        now = self._clock()
        self._evict_expired(now)
        entry = self._jobs.get(job_id)
        if entry is None:
            return None
        if entry.is_closed and entry.queue.empty():
            return None
        self._touch(entry, now)
        # fast-path：已有积压事件
        if not entry.queue.empty():
            return entry.queue.get_nowait()
        # 等待唤醒（producer 推事件后 set；close 时也会 set）
        try:
            await asyncio.wait_for(entry.event.wait(), timeout=timeout)
        except TimeoutError:
            return None
        # 唤醒后清旗 + 收事件
        entry.event.clear()
        if entry.queue.empty():
            # 被 close 唤醒但无事件 → 表示流结束
            return None
        return entry.queue.get_nowait()

    def close_job(self, job_id: str) -> None:
        """关闭 job：清空 state + 唤醒所有等待者。"""
        if not job_id:
            return  # 静默忽略空 id
        entry = self._jobs.pop(job_id, None)
        if entry is None:
            return
        entry.is_closed = True
        entry.event.set()


# ─────────────────────────────────────────────────────────────────────────────
# §五 模块级 singleton（懒初始化 + 线程安全）
# ─────────────────────────────────────────────────────────────────────────────
# 单实例 —— 与 ``app.state.job_state`` 一样属于"进程内 1 份"的资源。
# lifespan 里我们倾向用 ``app.state.job_state``（更显式），但本 accessor 留作
# ``get_job_state_store()`` 的全局 fallback，方便在 router / service 不依赖
# ``Request`` 注入时也能拿到同一份。
_singleton: JobStateStore | None = None
_singleton_lock: asyncio.Lock | None = None


def get_job_state_store() -> JobStateStore:
    """获取进程级 ``JobStateStore`` singleton（懒初始化）。

    Note:
        优先用 ``app.state.job_state``（lifespan 注入）。本 accessor 仅在
        ``Request`` 不可用（后台 task / 启动探针）场景兜底。

    """
    global _singleton
    if _singleton is None:
        _singleton = InMemoryJobStateStore()
    return _singleton


def reset_job_state_store() -> None:
    """重置 singleton（仅测试用）。"""
    global _singleton
    _singleton = None


__all__ = [
    "DEFAULT_JOB_TTL_SECONDS",
    "DEFAULT_NEXT_EVENT_TIMEOUT_SECONDS",
    "VALID_STATUSES",
    "InMemoryJobStateStore",
    "JobEvent",
    "JobStateError",
    "JobStateStore",
    "get_job_state_store",
    "reset_job_state_store",
]
