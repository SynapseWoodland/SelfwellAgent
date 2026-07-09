"""Unit tests for ``diagnosis_v1`` async path + jobs/{job_id}/stream SSE endpoint.

真源：docs/design/mvp_a_场景端到端实现方案_d1d163fa §4.1-§4.2 (PR-A2)

覆盖：
- POST /api/v1/diagnosis?async=true 返 202 + {job_id, status, stream_url}
- GET /api/v1/diagnosis/jobs/{job_id}/stream 拉 stage 事件 + done
- GET 流对未知 job_id 返 404 + E_DIAGNOSIS_JOB_NOT_FOUND
- LLM 注入失败时 stream 输出 error 事件
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.job_state import InMemoryJobStateStore


@pytest.fixture
def client_with_user():
    """Mock JWT 鉴权 + 注入 InMemoryJobStateStore 到 app.state。"""
    from app.api.deps import current_user_id, db_session
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return "u-async"

    fastapi_app.state.job_state = InMemoryJobStateStore()

    async def _fake_session() -> AsyncMock:
        s = AsyncMock()
        s.add = lambda _row: None
        s.flush = AsyncMock(return_value=None)
        s.commit = AsyncMock(return_value=None)
        s.bind = None
        return s

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    fastapi_app.dependency_overrides[db_session] = _fake_session
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)
    fastapi_app.dependency_overrides.pop(db_session, None)


def _post_body() -> dict:
    """最小合法 POST body（前端单图格式：objectKey 触发 1 张 face 占位 photo）。"""
    return {
        "objectKey": "uploads/test.jpg",
        "user_note": "最近焦虑",
    }


def test_post_async_returns_202_with_job_id_and_stream_url(client_with_user) -> None:
    """POST ``?async=true`` → 202 + {job_id, status:'queued', stream_url}。"""
    from app.api.routers import diagnosis_v1 as dv1

    async def fake_run(*args, **kwargs):
        return None

    with patch.object(dv1, "run_diagnosis_job", new=fake_run):
        resp = client_with_user.post(
            "/api/v1/diagnosis?async=true",
            json=_post_body(),
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["status"] == "queued"
    assert data.get("job_id")
    assert data["stream_url"] == f"/api/v1/diagnosis/jobs/{data['job_id']}/stream"


def test_post_sync_still_works_after_async_added(client_with_user) -> None:
    """POST 不带 ``?async=true`` → 走同步路径返 ``DiagnosisResponse``。"""
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


def test_get_stream_unknown_job_returns_404(client_with_user) -> None:
    """未知 job_id → 404 + E_DIAGNOSIS_JOB_NOT_FOUND。"""
    resp = client_with_user.get(
        "/api/v1/diagnosis/jobs/00000000-0000-0000-0000-000000000000/stream",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "E_DIAGNOSIS_JOB_NOT_FOUND"


def _build_diagnose_inputs(user_id: str, report_id: str, job_id: str):
    """构造 StreamDiagnoseInputs + AsyncMock db（两条测试共用）。"""
    from app.services.diagnosis_service import StreamDiagnoseInputs

    db = AsyncMock()

    class _Exec:
        def scalar_one_or_none(self):
            return None

    db.execute = AsyncMock(return_value=_Exec())
    db.flush = AsyncMock(return_value=None)

    return (
        StreamDiagnoseInputs(
            photos=[
                {"url": "f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 0},
            ],
            complaint=None,
            user_id=user_id,
            report_id=report_id,
            job_id=job_id,
            profile={},
        ),
        db,
    )


@pytest.mark.asyncio
async def test_async_get_stream_yields_stage_and_done_events_via_sse_gen() -> None:
    """绕过 HTTP 层：直接调 ``_job_event_stream``，确认 SSE 事件顺序。

    HTTP-层覆盖已在``test_async_get_stream_*`` 之外的 fastapi.TestClient 流测试
    间接覆盖（route 注册、headers、404 等）；本测试聚焦 SSE 生成器本身的协议合规性。
    """
    from app.api.routers import diagnosis_v1 as dv1
    from app.core.job_state import InMemoryJobStateStore
    from app.services.diagnosis_service import (
        stream_diagnose,
    )

    store = InMemoryJobStateStore()
    report_id = str(uuid4())
    job_id = store.create_job(report_id=report_id, user_id="u-async")
    inputs, db = _build_diagnose_inputs("u-async", report_id, job_id)

    async def fake_llm(*args, **kwargs):
        return {
            "directions": [{"title": "t", "description": "d", "video_id": None}],
            "tags": ["tg"],
            "summary": "sm",
            "llm_cost": "0",
            "model": "m",
        }

    async def _pipeline() -> None:
        with patch(
            "app.services.diagnosis_service._invoke_llm_structured",
            new=fake_llm,
        ):
            await stream_diagnose(inputs, store=store, db=db)

    pipeline_task = asyncio.create_task(_pipeline())

    # 直接消费 generator
    lines: list[str] = []
    gen = dv1._job_event_stream(store, job_id, "u-async")
    for _ in range(50):  # 上限防卡死
        try:
            line = await asyncio.wait_for(anext(gen), timeout=2.0)
        except (StopAsyncIteration, TimeoutError):
            break
        lines.append(line)
        if line.startswith("event: done"):
            break

    import contextlib

    with contextlib.suppress(RuntimeError):
        await asyncio.wait_for(pipeline_task, timeout=5.0)
    # 确保 generator 关闭
    await gen.aclose()

    body = "\n".join(lines)
    assert "event: stage" in body
    assert '"stage": "connected"' in body
    assert '"stage": "ready"' in body
    assert "event: done" in body


@pytest.mark.asyncio
async def test_async_get_stream_emits_error_event_on_pipeline_failure() -> None:
    """直接驱动 ``_job_event_stream`` generator：pipeline 失败时收到 error + code。

    HTTP-layer 路径在 test_get_stream_unknown_job_returns_404 已覆盖；本测试聚焦
    generator 把 error event 正确格式化的契约。
    """
    from app.api.routers import diagnosis_v1 as dv1
    from app.core.job_state import InMemoryJobStateStore
    from app.services.diagnosis_service import (
        stream_diagnose,
    )

    store = InMemoryJobStateStore()
    report_id = str(uuid4())
    job_id = store.create_job(report_id=report_id, user_id="u-async")
    inputs, db = _build_diagnose_inputs("u-async", report_id, job_id)

    async def boom(*args, **kwargs):
        raise RuntimeError("LLM 故障")

    async def _pipeline() -> None:
        import contextlib

        with (
            patch(
                "app.services.diagnosis_service._invoke_llm_structured",
                new=boom,
            ),
            contextlib.suppress(RuntimeError),
        ):
            await stream_diagnose(inputs, store=store, db=db)

    pipeline_task = asyncio.create_task(_pipeline())

    lines: list[str] = []
    gen = dv1._job_event_stream(store, job_id, "u-async")
    for _ in range(50):
        try:
            line = await asyncio.wait_for(anext(gen), timeout=2.0)
        except (StopAsyncIteration, TimeoutError):
            break
        lines.append(line)
        if line.startswith("event: error"):
            break

    import contextlib

    with contextlib.suppress(RuntimeError):
        await asyncio.wait_for(pipeline_task, timeout=5.0)
    await gen.aclose()

    body = "\n".join(lines)
    assert "event: error" in body
    assert '"code": "E_DIAGNOSIS_PIPELINE_FAILED"' in body
