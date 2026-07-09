"""Unit tests for ``/api/v1/diagnosis/{report_id}/stream`` SSE endpoint.

真源：M2 修复 #4（5 阶段 SSE）+ PR-A2 增量（async pipeline / jobs stream）。
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.job_state import InMemoryJobStateStore


@pytest.fixture
def client_with_user():
    r"""Mock JWT 鉴权：使用 lambda 替换 current_user_id，避免 AsyncMock 的

    ``*args, **kwargs`` 签名被 FastAPI 解析为 query 参数。

    参考 FastAPI issue #3331：``AsyncMock`` 的 inspect.signature 是 ``(*args, **kwargs)``，
    FastAPI 0.139 会要求 query 参数 args/kwargs，导致 422。
    """
    from app.api.deps import current_user_id
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return "u-stream"

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)


def test_stream_first_event_is_connected(client_with_user) -> None:
    r"""首事件必须是 ``event: stage\ndata: {\"stage\":\"connected\"}``。"""
    with patch(
        "app.api.routers.diagnosis_v1.get_report_status",
        new=AsyncMock(return_value="ready"),
    ):
        resp = client_with_user.get(
            "/api/v1/diagnosis/r-1/stream",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body = resp.text
    assert "event: stage" in body
    assert '"stage": "connected"' in body
    assert '"stage": "ready"' in body
    assert '"ok": true' in body


def test_stream_response_headers(client_with_user) -> None:
    """media-type 必须为 text/event-stream。"""
    with patch(
        "app.api.routers.diagnosis_v1.get_report_status",
        new=AsyncMock(return_value="ready"),
    ):
        resp = client_with_user.get(
            "/api/v1/diagnosis/r-2/stream",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.status_code == 200


def test_stream_error_on_timeout(client_with_user) -> None:
    """30s 超时 → 发 error(E_DIAGNOSIS_NOT_FOUND) 后关闭。"""
    from app.api.routers import diagnosis_v1 as dv1

    real_sleep = dv1.asyncio.sleep

    async def fast_sleep(seconds):
        await real_sleep(0.001)

    async def fake_get_status_never(session, *, user_id, report_id):
        return None

    with patch(
        "app.api.routers.diagnosis_v1.get_report_status", new=fake_get_status_never
    ), patch.object(dv1.asyncio, "sleep", new=fast_sleep):
        resp = client_with_user.get(
            "/api/v1/diagnosis/r-4/stream",
            headers={"Authorization": "Bearer fake"},
        )

    body = resp.text
    assert '"code": "E_DIAGNOSIS_NOT_FOUND"' in body
    assert "event: error" in body


# ════════════════════════════════════════════════════════════════════════════════
# PR-A2 增量 — async pipeline / jobs stream
# ════════════════════════════════════════════════════════════════════════════════


def _post_body() -> dict:
    """最小合法 POST body（前端单图格式：objectKey 触发 1 张 face 占位 photo）。"""
    return {
        "objectKey": "uploads/test.jpg",
        "user_note": "最近焦虑",
    }


def test_async_returns_job_id_and_202(client_with_user) -> None:
    """``POST ?async=true`` → 202 + {job_id, status, stream_url}。

    注入一个 InMemoryJobStateStore 到 ``app.state.job_state``，
    让 _handle_async_create 走真实路径但不让后台 task 真正跑 LLM。
    """
    from app.api.deps import db_session
    from app.api.routers import diagnosis_v1 as dv1
    from app.main import app as fastapi_app

    # 1. 注入 InMemoryJobStateStore 到 app.state
    if not hasattr(fastapi_app.state, "job_state"):
        fastapi_app.state.job_state = InMemoryJobStateStore()

    # 2. mock DB session：让 _handle_async_create 的 session.add/flush/commit 都不报错
    async def _fake_session() -> AsyncMock:
        s = AsyncMock()
        s.add = lambda _row: None
        s.flush = AsyncMock(return_value=None)
        s.commit = AsyncMock(return_value=None)
        s.bind = None
        return s

    fastapi_app.dependency_overrides[db_session] = _fake_session

    # 3. patch run_diagnosis_job 让其不做任何事（避免触发 LLM）
    async def fake_run(*args, **kwargs):
        return None

    try:
        with patch.object(dv1, "run_diagnosis_job", new=fake_run):
            resp = client_with_user.post(
                "/api/v1/diagnosis?async=true",
                json=_post_body(),
                headers={"Authorization": "Bearer fake"},
            )

        assert resp.status_code == 202
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "queued"
        assert body["data"]["stream_url"].startswith("/api/v1/diagnosis/jobs/")
        assert "job_id" in body["data"]
    finally:
        fastapi_app.dependency_overrides.pop(db_session, None)


def test_async_does_not_break_sync_path(client_with_user) -> None:
    """``POST`` 不带 ``?async=true`` → 走同步路径返 ``DiagnosisResponse``。

    同步路径 mock 掉 ``create_diagnosis`` 让其返一个最小 dict，校验返回结构不被 PR-A2 改动破坏。
    """
    from app.api.routers import diagnosis_v1 as dv1

    async def fake_create(*args, **kwargs):
        return {
            "directions": [{"title": "mock", "description": "mock", "video_id": None}],
            "tags": ["mock"],
            "summary": "mock",
            "cached": False,
            "llm_model": None,
            "llm_cost": "0",
            "report_id": None,
        }

    with patch.object(dv1, "create_diagnosis", new=fake_create):
        resp = client_with_user.post(
            "/api/v1/diagnosis",  # 注意：没有 ?async=
            json=_post_body(),
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["data"]["summary"] == "mock"


@pytest.mark.asyncio
async def test_stream_pipeline_stages_in_order() -> None:
    """驱动 ``stream_diagnose`` → 5 阶段 + done 事件按序出现。

    使用真实 InMemoryJobStateStore；background 调用方在另一个协程里消费 next_event。
    LLM 调用 patch 掉，避免真实 LLM 调用与 MockLLM 不支持的 `with_structured_output`。
    """
    from uuid import uuid4

    from app.core.job_state import InMemoryJobStateStore
    from app.services.diagnosis_service import (
        StreamDiagnoseInputs,
        stream_diagnose,
    )

    store = InMemoryJobStateStore()
    job_id = store.create_job(report_id=str(uuid4()), user_id="u-stream")
    report_id = str(uuid4())

    # Mock 的 db.execute() 应返回 None，不该触发 SQLAlchemy chain。
    db = AsyncMock()
    db.flush = AsyncMock(return_value=None)
    # db.execute 已被显式覆盖；scalar_one_or_none 必须返 None（让 _persist 走 INSERT 分支）

    class _Exec:
        def scalar_one_or_none(self):
            return None

    db.execute = AsyncMock(return_value=_Exec())

    inputs = StreamDiagnoseInputs(
        photos=[{"url": "uploads/test.jpg", "body_part": "face", "format": "jpg", "size_bytes": 0}],
        complaint="最近焦虑",
        user_id="u-stream",
        report_id=report_id,
        job_id=job_id,
        profile={"age_range": "20-25"},
    )

    consumer_task = asyncio.create_task(_collect_events(store, job_id, max_events=6))

    # 用 ``AsyncMock`` 直接替换 _invoke_llm_structured 的模块绑定，让 mock 自动 await；
    # 若用 ``new=fake_llm``，stream_diagnose 里的 ``await`` 仍会触发 fake_llm
    # 但 conftest 的 autouse MockLLM 会在 _invoke_llm_structured 内部被先调用，
    # 引发 AttributeError（MockLLM 没有 with_structured_output）。
    llm_mock = AsyncMock(
        return_value={
            "directions": [{"title": "mock", "description": "mock", "video_id": None}],
            "tags": ["mock"],
            "summary": "mock",
            "llm_cost": "0",
            "model": "mock",
        }
    )

    with patch(
        "app.services.diagnosis_service._invoke_llm_structured",
        new=llm_mock,
    ):
        await stream_diagnose(inputs, store=store, db=db)

    events = await consumer_task

    stages = [e["stage"] for e in events if e["kind"] == "stage"]
    assert stages == ["connected", "preprocess", "analyzing", "suggestion", "ready"]
    kinds = [e["kind"] for e in events]
    assert kinds[-1] == "done"
    # Report 对象未被真正插入（db.add 是 Mock），但 flush 被调用过
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_stream_emits_error_on_pipeline_failure() -> None:
    """LLM 抛异常 → stage:ready 之前发出 error 事件 + ``code=E_DIAGNOSIS_PIPELINE_FAILED``。

    不再依赖真实 LLM，直接 patch ``_invoke_llm_structured`` 抛异常。
    """
    from unittest.mock import AsyncMock
    from uuid import uuid4

    from app.core.job_state import InMemoryJobStateStore
    from app.services.diagnosis_service import (
        StreamDiagnoseInputs,
        stream_diagnose,
    )

    store = InMemoryJobStateStore()
    job_id = store.create_job(report_id=str(uuid4()), user_id="u-stream")
    report_id = str(uuid4())

    db = AsyncMock()
    db.flush = AsyncMock(return_value=None)

    inputs = StreamDiagnoseInputs(
        photos=[{"url": "uploads/test.jpg", "body_part": "face", "format": "jpg", "size_bytes": 0}],
        complaint=None,
        user_id="u-stream",
        report_id=report_id,
        job_id=job_id,
        profile={},
    )

    consumer_task = asyncio.create_task(_collect_events(store, job_id, max_events=10))

    async def boom(*args, **kwargs):
        raise RuntimeError("LLM 故障：测试强制异常")

    with patch.object(
        __import__("app.services.diagnosis_service", fromlist=["_invoke_llm_structured"]),
        "_invoke_llm_structured",
        new=boom,
    ), pytest.raises(RuntimeError):
        await stream_diagnose(inputs, store=store, db=db)

    events = await consumer_task
    error_events = [e for e in events if e["kind"] == "error"]
    assert len(error_events) == 1
    err = error_events[0]
    assert err["code"] == "E_DIAGNOSIS_PIPELINE_FAILED"
    assert "message_zh" in err


async def _collect_events(
    store: InMemoryJobStateStore, job_id: str, *, max_events: int = 10, timeout: float = 2.0
) -> list[dict]:
    """持续从 store 拉事件直到遇到 done/error 或超时。"""
    collected: list[dict] = []
    deadline = asyncio.get_event_loop().time() + timeout
    while len(collected) < max_events:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        evt = await store.next_event(job_id, timeout=min(remaining, 0.5))
        if evt is None:
            continue
        collected.append({"kind": evt.kind, **evt.payload})
        if evt.kind in {"done", "error"}:
            break
    return collected
