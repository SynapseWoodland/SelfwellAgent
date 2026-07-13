"""C-1 契约修复 smart_analyze 入口额外返回 report_id/job_id/stream_url."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_USER_ID = "u-smart-analyze-1"


class _AsyncSessionStub:
    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, *_args, **_kwargs) -> None:
        return None

    def add(self, _obj: object) -> None:
        return None


@pytest.fixture
def client_with_user():
    from app.api.deps import current_user_id, db_session
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return _USER_ID

    async def _override_db():
        yield _AsyncSessionStub()

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    fastapi_app.dependency_overrides[db_session] = _override_db
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)
    fastapi_app.dependency_overrides.pop(db_session, None)


@pytest.fixture(autouse=True)
def _patch_job_state():
    fake_job_state = MagicMock()
    fake_job_state.create_job = MagicMock(return_value="job-fixed-xyz123")
    p = patch("app.core.job_state.get_job_state_store", return_value=fake_job_state)
    p.start()
    yield
    p.stop()


def test_smart_analyze_returns_report_job_stream(client_with_user):
    resp = client_with_user.post(
        "/api/v1/assistant/sessions",
        json={"entry_card": "smart_analyze", "primary_intent": "smart_analyze"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json().get("data", resp.json())
    assert "report_id" in data
    assert "job_id" in data
    assert "stream_url" in data
    assert data["stream_url"].startswith("/diagnosis/jobs/")
    assert data["stream_url"].endswith("/stream")
    assert data["job_id"] == "job-fixed-xyz123"
    assert "session_id" in data


def test_non_smart_analyze_no_report_job(client_with_user):
    resp = client_with_user.post(
        "/api/v1/assistant/sessions",
        json={"entry_card": "mood_diary", "primary_intent": "mood_diary"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json().get("data", resp.json())
    assert "session_id" in data
    assert "report_id" not in data
    assert "job_id" not in data
    assert "stream_url" not in data


def test_default_intent_no_report_job(client_with_user):
    resp = client_with_user.post(
        "/api/v1/assistant/sessions",
        json={},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json().get("data", resp.json())
    assert "session_id" in data
    assert "report_id" not in data
    assert "job_id" not in data