"""Contract tests for ``GET /api/v1/plans/{plan_id}`` endpoint.

真源：``backend/app/api/routers/plans_v1.py``

锁定：
- 非 UUID 字符串（如 ``drafts``）由 FastAPI 在路由依赖解析阶段返回 422，
  避免非 UUID 字符串下推到 SQL 层触发 ``asyncpg.exceptions.DataError``。
  （历史教训：2026-07-12 前端误调 ``GET /plans/drafts`` 把 ``drafts`` 当
  ``plan_id``，导致 ``asyncpg.exceptions.DataError: invalid UUID 'drafts'``，
  详见错误堆栈 ``plan_service.py:283`` → ``plans_v1.py:146``。）
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


_USER_ID = "u-plan-id-test"


@pytest.fixture
def client_with_user():
    """Mock JWT 鉴权：使用 lambda 替换 current_user_id。"""
    from app.api.deps import current_user_id
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return _USER_ID

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)


def _install_plan_session() -> None:
    """覆盖 ``db_session`` 依赖：保证合法 UUID 路径下也能解析到 plan。"""
    from app.api.deps import db_session
    from app.main import app as fastapi_app

    plan_obj = MagicMock()
    plan_obj.id = "f255dff8-9f47-43a6-91c4-932b00c0447f"
    plan_obj.user_id = _USER_ID
    plan_obj.report_id = "r-1"
    plan_obj.days = {"items": []}
    plan_obj.status = "active"
    plan_obj.started_at = None
    plan_obj.deleted_at = None

    class _FakeScalarResult:
        def scalar_one_or_none(self_inner):
            return plan_obj

    class _FakeSession:
        def __init__(self_inner):
            self_inner.execute = AsyncMock(return_value=_FakeScalarResult())

    async def _override_db():
        yield _FakeSession()

    fastapi_app.dependency_overrides[db_session] = _override_db


def _clear_plan_session_override() -> None:
    from app.api.deps import db_session
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides.pop(db_session, None)


@pytest.mark.parametrize(
    "bad_plan_id",
    [
        "drafts",                                # 历史 bug：V2 前端臆造的接口名
        "not-a-uuid",
        "123",                                   # 太短
        "f255dff8-9f47-43a6-91c4-932b00c0447",  # 缺最后一位
        "f255dff8-9f47-43a6-91c4-932b00c0447g",  # 非法字符
        "draft",                                 # 长度刚好 < 32
    ],
)
def test_get_plan_rejects_non_uuid_path_param(
    client_with_user: TestClient,
    bad_plan_id: str,
) -> None:
    """非 UUID 路径参数 → 422，绝不触达 asyncpg。

    这是 2026-07-12 bug 的回归保护：把 Pydantic 类型从 ``str`` 收紧为 ``UUID``，
    非法值在依赖解析阶段被拦截。
    """
    _install_plan_session()
    try:
        resp = client_with_user.get(
            f"/api/v1/plans/{bad_plan_id}",
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        _clear_plan_session_override()

    assert resp.status_code == 422, (
        f"非 UUID plan_id={bad_plan_id!r} 应被 FastAPI 拒绝 (422)，"
        f"实际返回 {resp.status_code} {resp.text}"
    )


def test_get_plan_accepts_legal_uuid(
    client_with_user: TestClient,
) -> None:
    """合法 UUID 路径参数 → 200（不回退到 mock 也能跑通基础契约）。"""
    _install_plan_session()
    try:
        resp = client_with_user.get(
            "/api/v1/plans/f255dff8-9f47-43a6-91c4-932b00c0447f",
            headers={"Authorization": "Bearer fake"},
        )
    finally:
        _clear_plan_session_override()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["plan_id"] == "f255dff8-9f47-43a6-91c4-932b00c0447f"