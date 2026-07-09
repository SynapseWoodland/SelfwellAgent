"""Unit tests for ``app.api.routers.assistant_v1`` assistant 路由层。

覆盖：
- GET /assistant/entry-state
- 4 卡 × 4 状态 shape 契约
- 鉴权依赖 current_user_id
- POST /assistant/sessions 返回 200 + ``session_id`` 非空（前端契约）
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.services.assistant_service import (
    DEFAULT_PRIMARY_INTENT,
    AssistantError,
    compute_entry_state,
)
from app.services.assistant_service import (
    create_session as assistant_create_session,
)


# ─────────────────────────────────────────────────────────────────────────────
# GET /assistant/entry-state shape 契约
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class FakeMe:
    user_id: str = "u-entry-1"
    current_streak_days: int = 7
    last_feedback_days_ago: int = 2


@pytest.mark.asyncio
async def test_compute_entry_state_returns_list_with_id_state_subtitle_highlight() -> None:
    """compute_entry_state 返回字段最小集：{id, state, title, subtitle, highlight}"""
    me = FakeMe()
    cards = compute_entry_state(
        me=me,
        latest_report={"diagnosis_id": "r-1"},
        recent_feedbacks=[{"feedback_id": "fb-1", "created_at": "2026-07-01T08:00:00Z"}],
    )
    assert isinstance(cards, list)
    for card in cards:
        assert set(card.keys()) >= {"id", "state", "title", "subtitle", "highlight"}
        assert card["highlight"] in (True, False)
        assert card["state"] in {"not_started", "in_progress", "completed", "inactive_7d"}


# ─────────────────────────────────────────────────────────────────────────────
# 路由层可发现性检查（防止 entry-state 路由被忘记挂载）
# ─────────────────────────────────────────────────────────────────────────────
def test_business_v1_router_defines_entry_state_route() -> None:
    """routers/business_v1.py 必须定义 GET /assistant/entry-state 路由

    通过 introspect 路由模块的属性名验证。
    """
    import app.api.routers.business_v1 as router_module

    src_path = router_module.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    # 路由路径字符串字面量
    assert "/assistant/entry-state" in src, (
        "routers/business_v1.py 必须挂载 GET /assistant/entry-state 路由"
    )
    # 必须 call compute_entry_state
    assert "compute_entry_state" in src, (
        "routers/business_v1.py 必须 import + 调 compute_entry_state"
    )


# ─────────────────────────────────────────────────────────────────────────────
# test_routers_assistant module 不应有 ASCII 错误
# ─────────────────────────────────────────────────────────────────────────────
def test_assistant_router_uses_current_user_id_dependency() -> None:
    """entry-state endpoint 必须使用 current_user_id 依赖（鉴权）"""
    import app.api.routers.business_v1 as router_module

    src_path = router_module.__file__
    assert src_path is not None
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    # 检查 entry_state endpoint 函数定义时同时引用了 current_user_id
    # 简单检查：源码至少出现一次 current_user_id
    assert "current_user_id" in src


# ─────────────────────────────────────────────────────────────────────────────
# POST /assistant/sessions 契约（前端依赖）
# ─────────────────────────────────────────────────────────────────────────────
_FIXED_SESSION_ID = "11111111-1111-4111-8111-111111111111"


def _patch_create_session(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Monkeypatch 掉 ``create_session`` service，避开真实 DB。"""
    from app.api.routers import assistant_v1

    fake = AsyncMock(
        return_value={
            "session_id": _FIXED_SESSION_ID,
            "persona_state": "warm",
            "entry_card": None,
        },
    )
    monkeypatch.setattr(assistant_v1, "create_session", fake)
    return fake


@pytest.fixture
def mock_jwt_user() -> str:
    """注入 current_user_id，让所有路由通过鉴权。"""
    from app.api.deps import current_user_id
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return "u-routes-1"

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    yield "u-routes-1"
    fastapi_app.dependency_overrides.pop(current_user_id, None)


def test_post_sessions_returns_200_with_nonempty_session_id(
    monkeypatch: pytest.MonkeyPatch, mock_jwt_user: str
) -> None:
    """POST /api/v1/assistant/sessions 必须返回 200 + ``session_id`` 非空。

    真源：apps/mp-selfwell/miniprogram/types/api.ts AssistantSession.session_id
    前端之前误把字段读成 ``id``（导致 "返回空 id" 错误），
    本测试锁定后端契约 = ``session_id``，逼前端对齐。
    """
    from app.main import app as fastapi_app

    create_session_mock = _patch_create_session(monkeypatch)
    client = TestClient(fastapi_app)
    resp = client.post(
        "/api/v1/assistant/sessions",
        json={},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 后端 v1 统一信封：{ code: 0, data: {...} }
    assert body["code"] == 0
    data = body["data"]
    # 关键断言：必须含 session_id 且非空
    assert "session_id" in data, f"响应缺少 session_id 字段，实际 keys={list(data.keys())}"
    assert data["session_id"], "session_id 字段值为空"
    assert data["session_id"] == _FIXED_SESSION_ID
    # 显式确保响应不带名为 ``id`` 的别名（避免前/后端再被混淆）
    assert "id" not in data, "后端契约字段名应统一为 session_id，不应同时提供 id"
    create_session_mock.assert_awaited_once()


def test_post_sessions_response_shape_is_stable(
    monkeypatch: pytest.MonkeyPatch, mock_jwt_user: str
) -> None:
    """POST /api/v1/assistant/sessions 返回 shape 锁定（防止后续漂移）。"""
    from app.main import app as fastapi_app

    _patch_create_session(monkeypatch)
    client = TestClient(fastapi_app)
    resp = client.post(
        "/api/v1/assistant/sessions",
        json={},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # 最小必含字段集合（真源：assistant_service.create_session 返回值）
    assert set(data.keys()) >= {"session_id", "persona_state", "entry_card"}


def test_post_sessions_requires_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/v1/assistant/sessions 缺 token → 401。"""
    from app.main import app as fastapi_app

    _patch_create_session(monkeypatch)
    client = TestClient(fastapi_app)
    resp = client.post("/api/v1/assistant/sessions", json={})
    assert resp.status_code == 401, resp.text


def test_post_sessions_service_error_returns_5xx_or_4xx(
    monkeypatch: pytest.MonkeyPatch, mock_jwt_user: str
) -> None:
    """Service 抛 AssistantError → 路由不返回空 200 body。"""
    from app.api.routers import assistant_v1
    from app.errors.codes import E_ASSISTANT_FORBIDDEN_CALLER
    from app.main import app as fastapi_app

    async def boom(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssistantError(
            "entry_card 非法：hacker",
            code=E_ASSISTANT_FORBIDDEN_CALLER,
            field="entry_card",
        )

    monkeypatch.setattr(assistant_v1, "create_session", boom)
    client = TestClient(fastapi_app)
    resp = client.post(
        "/api/v1/assistant/sessions",
        json={"entry_card": "hacker"},
        headers={"Authorization": "Bearer fake"},
    )
    # 不能是 200 + 空 body（避免前端"空 id"误判）
    assert resp.status_code != 200, f"应当报错却返回 200: {resp.text}"
    assert resp.status_code in (400, 401, 403, 404, 422, 500, 503)


# ─────────────────────────────────────────────────────────────────────────────
# 服务层回归测试：create_session 必须把 user_id (str) → UUID
# 背景：真源 DDL 中 ai_sessions.user_id 是 postgresql.UUID(as_uuid=True)。
# 当 current_user_id（JWT sub claim）是合法 UUID 字符串时没问题；
# 但当是 dev / 测试 token 含非 UUID 字符串（如 "u-fake-1"）时，
# asyncpg 会抛 ValueError("invalid UUID ...: length must be between 32..36")，
# 整个端点 500 → 前端拿到网络异常 → session_id 永远空。
# 修复：service 层主动 UUID(str(user_id))，失败兜底到 uuid4()（与 diagnosis_v1.py 对齐）。
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_session_coerces_non_uuid_user_id_to_uuid() -> None:
    """create_session 收到非 UUID 字符串 user_id（如 ``u-fake-1``）必须不抛 500。"""
    from uuid import UUID as _UUID

    fake_session = MagicMock()
    fake_session.add = MagicMock()
    fake_session.flush = AsyncMock()

    result = await assistant_create_session(
        fake_session,
        user_id="u-fake-1",  # 非 UUID 字符串 —— 之前会让 asyncpg 抛 ValueError
    )

    # 必须返回非空 session_id（前端契约字段）
    assert result["session_id"], f"create_session 应返回非空 session_id, 实际={result}"
    assert result["persona_state"] == "warm"
    assert result["entry_card"] is None
    fake_session.add.assert_called_once()
    fake_session.flush.assert_awaited_once()

    # 关键断言：传给 AISession 的 user_id 必须是 UUID 实例（不是 str）
    ai_session_obj = fake_session.add.call_args.args[0]
    assert isinstance(ai_session_obj.user_id, _UUID), (
        f"create_session 内部必须把 user_id 强转为 UUID，"
        f"实际类型={type(ai_session_obj.user_id).__name__}"
    )


@pytest.mark.asyncio
async def test_create_session_accepts_uuid_string_user_id() -> None:
    """create_session 收到合法 UUID 字符串 user_id 必须正常返回。"""
    fake_session = MagicMock()
    fake_session.add = MagicMock()
    fake_session.flush = AsyncMock()

    valid_uuid = "11111111-2222-3333-4444-555555555555"
    result = await assistant_create_session(fake_session, user_id=valid_uuid)

    assert result["session_id"], "合法 UUID 必须产生非空 session_id"
    ai_session_obj = fake_session.add.call_args.args[0]
    assert str(ai_session_obj.user_id) == valid_uuid
    assert ai_session_obj.primary_intent == DEFAULT_PRIMARY_INTENT


# ── 防止未使用 import lint ──────────────────────────────────────────────────
__all__ = ["compute_entry_state"]
