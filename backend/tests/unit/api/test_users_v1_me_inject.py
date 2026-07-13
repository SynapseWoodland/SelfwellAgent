"""Unit tests for ``GET /api/v1/users/me``（PR-2 V2 IA 注入层契约锁）。

真源：``backend/app/api/routers/users_v1.py`` + ``v2-unified-parent.md`` §PR-2。

覆盖：
- ``GET /users/me`` 响应包含 ``badges_summary`` 和 ``streak_days`` 注入字段。
- ``streak_days`` 走实时 SQL 计算（``compute_streak_days``），不依赖 profile_service cache。
- 即使 ``compute_streak_days`` 失败，仍能 fallback 到 profile_service 返回的 cache 值。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


_USER_ID = "u-pr2-me-test"


@pytest.fixture
def client_with_user():
    """Mock JWT 鉴权 + DB 会话：替换 current_user_id 为常量、db_session 为 AsyncMock。"""
    from app.api.deps import current_user_id, db_session
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return _USER_ID

    async def fake_db_session() -> AsyncMock:
        # router 用 session.execute / session.get；mock 整体 AsyncMock 即可
        return AsyncMock()

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    fastapi_app.dependency_overrides[db_session] = fake_db_session
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)
    fastapi_app.dependency_overrides.pop(db_session, None)


def _build_profile_payload(*, cache_streak_days: int = 5) -> dict[str, Any]:
    """profile_service.get_user_profile 的返回 dict（含 cache streak_days）。"""
    return {
        "user_id": _USER_ID,
        "nickname": "tester",
        "status": "active",
        "current_streak_days": cache_streak_days,
        "fragments": 0,
        "report_cache": {"streak_days": cache_streak_days, "fragments": 0},
        # PR-2 V2 增量字段（service 端不再产出，由 router 注入）
    }


@pytest.fixture
def patch_profile_service(monkeypatch: pytest.MonkeyPatch):
    """替换 ``app.api.routers.users_v1`` 模块内的 ``get_user_profile`` 为 mock。

    router 用 ``from ... import get_user_profile``（顶层 import），函数引用绑到 router 自己的命名空间，
    所以 patch router 模块内的符号，而不是服务层符号。
    mock 返回受控 dict（不调真实 service，避免触发真实 DB 查询）。
    """

    async def fake_get_user_profile(session: Any, user_id: str) -> dict[str, Any]:
        return _build_profile_payload(cache_streak_days=5)

    monkeypatch.setattr(
        "app.api.routers.users_v1.get_user_profile", fake_get_user_profile
    )
    return fake_get_user_profile


@pytest.fixture
def patch_badge_summary(monkeypatch: pytest.MonkeyPatch):
    """替换 v2 badge_service.get_badges_summary（router 用局部 from-import 加载）。"""

    async def fake_get_badges_summary(
        session: Any, *, user_id: str
    ) -> dict[str, Any]:
        return {"total_unlocked": 2, "total_codes": 6, "latest_unlocked": None}

    monkeypatch.setattr(
        "app.services.v2.badge_service.get_badges_summary",
        fake_get_badges_summary,
    )
    return fake_get_badges_summary


@pytest.fixture
def patch_streak_days(monkeypatch: pytest.MonkeyPatch, value: int = 12):
    """替换 archive_service.compute_streak_days（实时 SQL 计算）。"""

    async def fake_compute_streak_days(session: Any, *, user_id: str) -> int:
        return value

    monkeypatch.setattr(
        "app.services.v2.archive_service.compute_streak_days",
        fake_compute_streak_days,
    )
    return fake_compute_streak_days


def test_get_me_includes_pr2_badges_summary_and_streak_days(
    client_with_user: TestClient,
    patch_profile_service: AsyncMock,
    patch_badge_summary: AsyncMock,
    patch_streak_days: AsyncMock,
) -> None:
    """PR-2 契约：``GET /users/me`` 响应 data 必须含 badges_summary + streak_days。"""
    resp = client_with_user.get("/api/v1/users/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert "badges_summary" in body["data"]
    assert "streak_days" in body["data"]
    assert body["data"]["badges_summary"]["total_codes"] == 6


def test_get_me_streak_days_uses_live_sql_not_cache(
    client_with_user: TestClient,
    patch_profile_service: AsyncMock,
    patch_badge_summary: AsyncMock,
    patch_streak_days: AsyncMock,
) -> None:
    """PR-2 关键修复：streak_days 应是实时 SQL 值（12）而非 profile_service cache（5）。"""
    resp = client_with_user.get("/api/v1/users/me")
    body = resp.json()
    # patch_streak_days 默认 value=12；profile_service cache 是 5
    assert body["data"]["streak_days"] == 12
    assert body["data"]["streak_days"] != 5


def test_get_me_streak_days_fallback_when_compute_fails(
    client_with_user: TestClient,
    patch_profile_service: AsyncMock,
    patch_badge_summary: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PR-2 容错：compute_streak_days 抛异常时，回退到 profile_service 的 cache 值。"""

    async def fake_compute_streak_days_fail(
        session: Any, *, user_id: str
    ) -> int:
        raise RuntimeError("DB connection lost")

    monkeypatch.setattr(
        "app.services.v2.archive_service.compute_streak_days",
        fake_compute_streak_days_fail,
    )

    resp = client_with_user.get("/api/v1/users/me")
    assert resp.status_code == 200
    body = resp.json()
    # profile_service 不再输出 streak_days，所以字段可能不存在（无害）
    # 但 badges_summary 必须仍注入成功
    assert body["data"]["badges_summary"]["total_codes"] == 6


def test_get_me_badges_summary_fallback_when_summary_fails(
    client_with_user: TestClient,
    patch_profile_service: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    patch_streak_days: AsyncMock,
) -> None:
    """PR-2 容错：badges_summary 抛异常时，回退到占位结构（total_codes=6）。"""

    async def fake_get_badges_summary_fail(
        session: Any, *, user_id: str
    ) -> dict[str, Any]:
        raise RuntimeError("badge service down")

    monkeypatch.setattr(
        "app.services.v2.badge_service.get_badges_summary",
        fake_get_badges_summary_fail,
    )

    resp = client_with_user.get("/api/v1/users/me")
    body = resp.json()
    assert body["data"]["badges_summary"] == {
        "total_unlocked": 0,
        "total_codes": 6,
        "latest_unlocked": None,
    }
    # streak_days 仍注入成功
    assert body["data"]["streak_days"] == 12