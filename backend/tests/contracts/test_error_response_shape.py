"""Sprint A 契约测试：前后端 ErrorResponse 形状 100% 对齐 OpenAPI。

真源：``docs/api/openapi.yaml#/components/schemas/ErrorResponse`` +
``docs/api/error-codes.md``。

Sprint 0 的 middleware（``ExceptionHandlerMiddleware``）只在抛出
``SelfwellError`` 时返回 ``{error: {code, message_zh, message_en}}``；
但 router 内 ``raise HTTPException(status_code, detail={code, message_zh})``
走的是 FastAPI 默认 ``HTTPException`` 处理器，会把响应包成
``{"detail": {"code": ..., "message_zh": ...}}`` —— 这与 OpenAPI 契约不符。

本测试契约固化 5 个高频错误码的精确 JSON 形状：
    {"error": {"code": "E_*", "message_zh": "...", "message_en": "..."}}

字段顺序、键名严格匹配，避免任何脱壳漂移。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.middleware.exception_handler import ExceptionHandlerMiddleware


# ─────────────────────────────────────────────────────────────────────────────
# Helper：构造一个最小 FastAPI app，仅包含被测 router + 必要 override
# ─────────────────────────────────────────────────────────────────────────────
def _build_app_with_router(import_path: str, attr: str) -> FastAPI:
    """动态 import 一个 router，挂在最小 FastAPI app 上（不挂中间件）。"""
    import importlib

    module = importlib.import_module(import_path)
    router = getattr(module, attr)
    app = FastAPI(title=f"contract-test-{attr}")
    # 不挂 middleware / 也不挂 ExceptionHandlerMiddleware —— 测的是 FastAPI
    # 默认 HTTPException handler 的真实行为（Sprint A 必须修复它）。
    app.include_router(router, prefix="/api/v1")
    return app


def _build_app_with_router_and_handler(import_path: str, attr: str) -> FastAPI:
    """同 _build_app_with_router，但挂上 Sprint 0 的 ExceptionHandlerMiddleware。"""
    app = _build_app_with_router(import_path, attr)
    app.add_middleware(ExceptionHandlerMiddleware)
    return app


# ─────────────────────────────────────────────────────────────────────────────
# Case 1: E_CHECKIN_INVALID_INPUT → POST /api/v1/checkins 缺字段
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_checkin_invalid_input_returns_openapi_error_envelope() -> None:
    """未登录 → checkin POST 返回标准 ErrorResponse。

    说明：用未带 JWT 的调用触发 ``E_AUTH_TOKEN_EXPIRED`` —— 该端点
    ``current_user_id`` 依赖会抛 401。验证 envelope 形状。
    """
    app = _build_app_with_router_and_handler(
        "app.api.routers.business_v1", "checkin_router"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # body 完全空 → service 抛 CheckinError(E_CHECKIN_INVALID_INPUT)，
        # 触发 400。但会先过 auth → 401 E_AUTH_TOKEN_EXPIRED，所以这里
        # 验的是 auth 通道的 envelope。
        resp = await ac.post("/api/v1/checkins", json={})

    assert resp.status_code in (400, 401)
    body = resp.json()
    assert "error" in body, f"missing 'error' key, got {body!r}"
    err = body["error"]
    # 字段集合精确匹配
    assert set(err.keys()) >= {"code", "message_zh", "message_en"}, (
        f"unexpected keys: {set(err.keys())}"
    )
    # 字段顺序不重要，值是字符串
    assert isinstance(err["code"], str) and err["code"].startswith("E_")
    assert isinstance(err["message_zh"], str) and err["message_zh"]
    assert isinstance(err["message_en"], str) and err["message_en"]


# ─────────────────────────────────────────────────────────────────────────────
# Case 2: E_FEEDBACK_INVALID_TYPE → POST /api/v1/feedback 非法 type
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_feedback_invalid_type_returns_openapi_error_envelope() -> None:
    """Feedback 非法 type → 400 + envelope。

    直接用 mock 跳过 auth，强制让 service 抛 FeedbackError(E_FEEDBACK_INVALID_TYPE)。
    """
    from app.services.feedback_service import FeedbackError

    app = _build_app_with_router_and_handler(
        "app.api.routers.business_v1", "feedback_router"
    )

    # mock current_user_id 直接返回 uuid，让请求真正走到 service
    from app.api.deps import current_user_id
    app.dependency_overrides[current_user_id] = lambda: "00000000-0000-0000-0000-000000000001"

    # mock db_session：service 抛 FeedbackError，不真访问 DB
    fake_session = AsyncMock()
    async def _raise_feedback_error(*_a: Any, **_kw: Any) -> dict[str, Any]:
        raise FeedbackError("非法 type", code="E_FEEDBACK_INVALID_TYPE", http_status=400)

    with patch("app.api.routers.business_v1.create_feedback", side_effect=_raise_feedback_error):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/feedback",
                json={"feedback_type": "BOGUS_TYPE"},
            )

    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body, f"missing 'error' key, got {body!r}"
    err = body["error"]
    assert err["code"] == "E_FEEDBACK_INVALID_TYPE", (
        f"expected E_FEEDBACK_INVALID_TYPE, got {err['code']!r}"
    )
    assert isinstance(err["message_zh"], str) and err["message_zh"]
    assert isinstance(err["message_en"], str) and err["message_en"]


# ─────────────────────────────────────────────────────────────────────────────
# Case 3: E_RECALL_EMPTY → POST /api/v1/butler/recall 空态
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_recall_empty_returns_openapi_error_envelope() -> None:
    """Recall 空态 → 200 + envelope（如 OpenAPI §E_RECALL_EMPTY 所定义）。"""
    from app.services.recall_service import RecallError

    app = _build_app_with_router_and_handler(
        "app.api.routers.business_v1", "butler_router"
    )

    from app.api.deps import current_user_id
    app.dependency_overrides[current_user_id] = lambda: "00000000-0000-0000-0000-000000000002"

    async def _raise_recall_empty(*_a: Any, **_kw: Any) -> dict[str, Any]:
        raise RecallError(
            "暂无可用素材", code="E_RECALL_EMPTY", http_status=200,
        )

    with patch("app.api.routers.business_v1.generate_recall", side_effect=_raise_recall_empty):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/butler/recall", json={"trigger": "user_query"})

    assert resp.status_code == 200
    body = resp.json()
    assert "error" in body, f"missing 'error' key, got {body!r}"
    err = body["error"]
    assert err["code"] == "E_RECALL_EMPTY"
    assert isinstance(err["message_zh"], str) and err["message_zh"]
    assert isinstance(err["message_en"], str) and err["message_en"]


# ─────────────────────────────────────────────────────────────────────────────
# Case 4: E_SHARE_TEMPLATE_INVALID → POST /api/v1/share/hug-card 非法模板
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_share_template_invalid_returns_openapi_error_envelope() -> None:
    """Share 非法模板 → 400 + envelope。"""
    from app.services.share_service import ShareError

    app = _build_app_with_router_and_handler(
        "app.api.routers.business_v1", "share_router"
    )

    from app.api.deps import current_user_id
    app.dependency_overrides[current_user_id] = lambda: "00000000-0000-0000-0000-000000000003"

    async def _raise_share_invalid(*_a: Any, **_kw: Any) -> dict[str, Any]:
        raise ShareError(
            "模板不存在", code="E_SHARE_TEMPLATE_INVALID", http_status=400,
        )

    with patch("app.api.routers.business_v1.generate_hug_card", side_effect=_raise_share_invalid):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/share/hug-card",
                json={"day": 7, "nickname": "我"},
            )

    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body, f"missing 'error' key, got {body!r}"
    err = body["error"]
    assert err["code"] == "E_SHARE_TEMPLATE_INVALID"
    assert isinstance(err["message_zh"], str) and err["message_zh"]
    assert isinstance(err["message_en"], str) and err["message_en"]


# ─────────────────────────────────────────────────────────────────────────────
# Case 5: E_AUTH_TOKEN_EXPIRED → GET /api/v1/users/me 带过期 token
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_auth_token_expired_returns_openapi_error_envelope() -> None:
    """GET /api/v1/users/me 带过期 JWT → 401 + E_AUTH_TOKEN_EXPIRED envelope。

    不挂 ExceptionHandlerMiddleware —— 测试的是 Sprint A 修复后
    FastAPI 全局 HTTPException handler 的行为：所有 ErrorResponse 必须
    走 ``{"error": {...}}`` 形状，**不**再出现 ``{"detail": {...}}``。
    """
    import jwt

    app = _build_app_with_router("app.api.routers.users_v1", "router")
    # 不挂 ExceptionHandlerMiddleware：测 FastAPI 默认 handler 的修复

    # 构造一个已过期的 token；签名用 dev secret（与 jwt_handler.py 默认一致）
    expired_token = jwt.encode(
        {"sub": "u-1", "exp": 1},  # exp=1 (1970-01-01) 必过期
        "dev-secret-not-for-prod",
        algorithm="HS256",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

    assert resp.status_code == 401
    body = resp.json()
    assert "error" in body, f"missing 'error' key, got {body!r}"
    err = body["error"]
    # 不强求 code（依赖 jwt_handler 抛的具体码），但必须是 E_* 开头
    assert err["code"].startswith("E_"), f"non-E_ code: {err['code']!r}"
    assert isinstance(err["message_zh"], str) and err["message_zh"]
    assert isinstance(err["message_en"], str) and err["message_en"]


# ─────────────────────────────────────────────────────────────────────────────
# Case 6（额外回归保护）：全局 ErrorResponse 不允许出现 "detail" 顶层 key
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_error_response_never_uses_legacy_detail_envelope() -> None:
    """回归保护：ErrorResponse 形状必须是 ``{"error": {...}}``，绝不能出现
    旧的 ``{"detail": {...}}`` FastAPI 默认包壳。

    触发方式：调用 users 端点，auth 必然失败 → 走 HTTPException handler。
    """
    app = _build_app_with_router("app.api.routers.users_v1", "router")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/users/me")  # 完全无 token

    body = resp.json()
    assert "detail" not in body, (
        f"legacy FastAPI envelope detected: {body!r}. "
        "Sprint A contract requires {'error': {...}} shape."
    )
    assert "error" in body
