"""Unit tests for ``GET /api/v1/plans/current?view=today|all`` endpoint.

真源：``backend/app/api/routers/plans_v1.py`` + MVP A 场景 §4.3。

覆盖：
- ``view=all`` 返回 3 周 21 天聚合（weeks 字段 + current_day_index）。
- ``view=today``（默认）保持原契约：直接透传 ``get_current_plan`` 的 dict。
- ``view`` 默认值 = ``today``。
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


_USER_ID = "u-view-test"


@pytest.fixture
def client_with_user():
    """Mock JWT 鉴权：使用 lambda 替换 current_user_id，避免 AsyncMock 的
    ``(*args, **kwargs)`` 签名被 FastAPI 解析为 query 参数。
    """
    from app.api.deps import current_user_id
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return _USER_ID

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)


def _build_plan_payload(started_at: date | None = None) -> dict:
    days = [
        {
            "day": d,
            "phase": 1 if d <= 7 else (2 if d <= 14 else 3),
            "tasks": [{"video_id": f"v-{d}-{i}"} for i in range(1)],
        }
        for d in range(1, 22)
    ]
    return {
        "id": "p-view-1",
        "user_id": _USER_ID,
        "report_id": "r-1",
        "days": {"items": days},
        "status": "active",
        "started_at": started_at,
    }


def _install_plan_session(started_at: date | None) -> None:
    """覆盖 ``db_session`` 依赖：返回 mock session。

    路由链路：
    1. ``_load_current_plan_orm`` → ``session.execute(select(Plan))`` → 返回 Plan ORM。
    2. ``get_plan`` → ``session.execute(select(Plan).where(id=...))`` → 返回 Plan ORM。
    """
    from app.api.deps import db_session
    from app.main import app as fastapi_app

    plan_obj = MagicMock()
    plan_obj.id = "p-view-1"
    plan_obj.user_id = _USER_ID
    plan_obj.report_id = "r-1"
    plan_obj.days = _build_plan_payload(started_at)["days"]
    plan_obj.status = "active"
    plan_obj.started_at = started_at
    plan_obj.deleted_at = None

    fake_session = _FakeSession(plan_obj)

    async def _override_db():
        yield fake_session

    fastapi_app.dependency_overrides[db_session] = _override_db


def _clear_plan_session_override() -> None:
    from app.api.deps import db_session
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides.pop(db_session, None)


class _FakeSession:
    """极简 AsyncSession 双替身：``execute`` 始终返回 ``plan_obj``。"""

    def __init__(self, plan_obj: MagicMock) -> None:
        self._plan = plan_obj
        self.execute = AsyncMock(return_value=_FakeScalarResult(plan_obj))


class _FakeScalarResult:
    def __init__(self, plan_obj: MagicMock) -> None:
        self._plan = plan_obj

    def scalar_one_or_none(self):
        return self._plan


def test_view_all_returns_weeks(
    client_with_user: TestClient,
) -> None:
    """``?view=all`` 返回 ``weeks[3]`` + ``current_day_index`` + 顶层字段。"""
    started = date(2026, 7, 8)
    _install_plan_session(started_at=started)
    try:
        resp = client_with_user.get(
            "/api/v1/plans/current",
            params={"view": "all"},
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        _clear_plan_session_override()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["plan_id"] == "p-view-1"
    assert data["total_days"] == 21
    assert data["view"] == "all"
    assert data["started_at"] == started.isoformat()
    assert data["current_day_index"] == 1
    weeks = data["weeks"]
    assert len(weeks) == 3
    assert [w["week_no"] for w in weeks] == [1, 2, 3]
    assert [w["title"] for w in weeks] == [
        "第一阶段 · 习惯启动",
        "第二阶段 · 强化提升",
        "第三阶段 · 稳定养成",
    ]
    for w in weeks:
        assert len(w["days"]) == 7
        for cell in w["days"]:
            assert set(cell.keys()) >= {"day", "state", "tasks_count", "phase"}
            assert cell["state"] in {"done", "today", "locked"}


def test_view_today_unchanged_legacy_response(
    client_with_user: TestClient,
) -> None:
    """``?view=today`` 显式传值 → 与原契约 100% 兼容（顶层字段集不变）。

    ``get_current_plan`` 内部走 ``session.execute(select(Plan))`` → ``get_plan``。
    """
    started = date(2026, 7, 8)
    _install_plan_session(started_at=started)
    try:
        resp = client_with_user.get(
            "/api/v1/plans/current",
            params={"view": "today"},
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        _clear_plan_session_override()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert "weeks" not in data, data
    assert "view" not in data, data
    assert "current_day_index" not in data, data
    assert data["plan_id"] == "p-view-1"
    assert data["days"][0]["day"] == 1


def test_view_default_is_today(
    client_with_user: TestClient,
) -> None:
    """不带 ``view`` 查询参数 → 默认 ``view=today``（与原契约一致）。"""
    started = date(2026, 7, 8)
    _install_plan_session(started_at=started)
    try:
        resp = client_with_user.get(
            "/api/v1/plans/current",
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        _clear_plan_session_override()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = body["data"]
    assert "weeks" not in data
    assert data["plan_id"] == "p-view-1"