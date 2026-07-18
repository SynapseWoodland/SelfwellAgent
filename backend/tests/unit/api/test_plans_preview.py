"""C-3 契约修复 · ``GET /plans/{plan_id}/preview?days=N`` 端点新增。

真源:docs/spec/TDS-M4-PR-Contract-Fix.md §C-3。

前端 plan-delivery/index.ts:loadPreview 调用契约:
- Path: ``/plans/{plan_id}/preview``
- Query: ``?days=21``
- Response.data.days: array of
    { day, day_index, title, task, duration_minutes, source, status }
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

_USER_ID = "u-preview-test"
_PLAN_ID = "p-preview-1"


@pytest.fixture
def client_with_user():
    from app.api.deps import current_user_id
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return _USER_ID

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)


def _install_get_plan_override(days_payload: list[dict]) -> None:
    """覆盖 ``db_session`` 依赖,让 ``get_plan`` 返回构造好的 days。

    ``get_plan`` 链路: ``session.execute(select(Plan).where(...))`` → scalar_one_or_none
    """
    from app.api.deps import db_session
    from app.main import app as fastapi_app

    plan_obj = MagicMock()
    plan_obj.id = _PLAN_ID
    plan_obj.user_id = _USER_ID
    plan_obj.report_id = "r-preview-1"
    plan_obj.days = {"items": days_payload}
    plan_obj.status = "active"
    plan_obj.started_at = None
    plan_obj.deleted_at = None

    fake_session = _FakeSession(plan_obj)

    async def _override_db():
        yield fake_session

    fastapi_app.dependency_overrides[db_session] = _override_db


def _clear_db_override() -> None:
    from app.api.deps import db_session
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides.pop(db_session, None)


class _FakeSession:
    def __init__(self, plan_obj):
        self._plan = plan_obj
        self.execute = AsyncMock(return_value=_FakeScalarResult(plan_obj))


class _FakeScalarResult:
    def __init__(self, plan_obj):
        self._plan = plan_obj

    def scalar_one_or_none(self):
        return self._plan


def _build_plan_days() -> list[dict]:
    """构造 21 天的 Plan.days.items,字段用 plan service 真实写入格式。"""
    return [
        {
            "day": d,
            "phase": 1 if d <= 7 else (2 if d <= 14 else 3),
            "tasks": [
                {
                    "video_id": f"v-{d}-1",
                    "title": f"Day {d} · 核心动作",
                    "duration_minutes": 12,
                    "source": "video_pool",
                    "status": "pending",
                }
            ],
        }
        for d in range(1, 22)
    ]


def test_preview_default_21_days(client_with_user: TestClient) -> None:
    """AC-1 ``GET /plans/{id}/preview`` 默认返 21 天,且字段映射满足前端契约。"""
    days = _build_plan_days()
    _install_get_plan_override(days)
    try:
        resp = client_with_user.get(
            f"/api/v1/plans/{_PLAN_ID}/preview",
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        _clear_db_override()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["plan_id"] == _PLAN_ID
    out_days = data["days"]
    assert len(out_days) == 21
    # 字段契约:前端 plan-delivery/index.ts:64 期望
    # source.{day, day_index, title, task, duration_minutes, source, status}
    sample = out_days[0]
    assert "day" in sample
    assert "title" in sample
    assert "duration_minutes" in sample
    assert "source" in sample
    assert "status" in sample
    # 第一天正确
    assert sample["day"] == 1
    assert sample["duration_minutes"] == 12


def test_preview_with_days_query_truncates(client_with_user: TestClient) -> None:
    """AC-2 ``?days=7`` → 只返前 7 天(避免给前端倒数据)。"""
    days = _build_plan_days()
    _install_get_plan_override(days)
    try:
        resp = client_with_user.get(
            f"/api/v1/plans/{_PLAN_ID}/preview",
            params={"days": 7},
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        _clear_db_override()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    out_days = body["data"]["days"]
    assert len(out_days) == 7
    assert [d["day"] for d in out_days] == list(range(1, 8))


def test_preview_plan_not_found_returns_404(client_with_user: TestClient) -> None:
    """AC-3 plan 不存在 → 404 + 业务错误码。"""
    from app.api.deps import db_session
    from app.main import app as fastapi_app

    # 让 scalar_one_or_none 返回 None
    class _NullSession:
        async def execute(self, *a, **kw):
            class _R:
                def scalar_one_or_none(self_inner):
                    return None

            return _R()

    async def _override():
        yield _NullSession()

    fastapi_app.dependency_overrides[db_session] = _override
    try:
        resp = client_with_user.get(
            "/api/v1/plans/missing-plan/preview",
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        fastapi_app.dependency_overrides.pop(db_session, None)
    # 期望 4xx(404 优先)
    assert resp.status_code in (404, 400), resp.text
    body = resp.json()
    assert body.get("code", 0) != 0 or "message_zh" in body.get("detail", {})