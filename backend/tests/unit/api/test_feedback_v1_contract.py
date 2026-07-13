"""Unit tests for ``POST /api/v1/feedback`` endpoint（PR-2 V2 IA 契约锁）。

真源：``backend/app/api/routers/feedback_v1.py`` + ``v2-unified-parent.md`` §PR-2。

覆盖：
- ``POST /feedback`` 响应字段集严格等于 7 个契约字段
  （feedback_id / ack_text / ai_session_id / ack / feedback_type / body_part / created_at）。
- 不透传 service 返回的多余字段，避免 service 增字段破坏前端契约稳定性。
- ``ai_session_id`` 当前为 ``None``（PR-2 未联动 AI 会话）。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


_USER_ID = "u-feedback-test"
_PR2_FEEDBACK_CONTRACT_KEYS: frozenset[str] = frozenset(
    {
        "feedback_id",
        "ack_text",
        "ai_session_id",
        "ack",
        "feedback_type",
        "body_part",
        "created_at",
    }
)


@pytest.fixture
def client_with_user():
    """Mock JWT 鉴权 + DB 会话。"""
    from app.api.deps import current_user_id, db_session
    from app.main import app as fastapi_app

    async def fake_user_id() -> str:
        return _USER_ID

    async def fake_db_session() -> AsyncMock:
        return AsyncMock()

    fastapi_app.dependency_overrides[current_user_id] = fake_user_id
    fastapi_app.dependency_overrides[db_session] = fake_db_session
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.pop(current_user_id, None)
    fastapi_app.dependency_overrides.pop(db_session, None)


@pytest.fixture
def patch_feedback_service(monkeypatch: pytest.MonkeyPatch):
    """替换 ``create_feedback`` service 为 mock，返回受控 dict（含 1 个多余字段）。"""

    async def fake_create_feedback(
        session: Any,
        *,
        user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "feedback_id": "fb-1",
            "feedback_type": payload.get("feedback_type", "general"),
            "body_part": payload.get("body_part"),
            "ack": "已收到反馈，谢谢！",
            "ack_text": "已收到反馈，谢谢！",
            "ai_session_id": None,
            "created_at": "2026-07-12T20:00:00+00:00",
            # service 层加的多余字段：不应漏到 response
            "_internal_audit_tag": "audit-12345",
        }

    monkeypatch.setattr(
        "app.api.routers.feedback_v1.create_feedback", fake_create_feedback
    )
    return fake_create_feedback


def test_post_feedback_returns_pr2_contract_keys(
    client_with_user: TestClient, patch_feedback_service: AsyncMock
) -> None:
    """PR-2 契约：response.data 字段集必须 == 7 个契约字段。"""
    resp = client_with_user.post(
        "/api/v1/feedback",
        json={"feedback_type": "general", "text_content": "打卡困难"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert set(body["data"].keys()) == _PR2_FEEDBACK_CONTRACT_KEYS


def test_post_feedback_does_not_leak_internal_fields(
    client_with_user: TestClient, patch_feedback_service: AsyncMock
) -> None:
    """PR-2 契约：service 加的 ``_internal_audit_tag`` 不能漏到前端。"""
    resp = client_with_user.post(
        "/api/v1/feedback",
        json={"feedback_type": "general"},
    )
    body = resp.json()
    assert "_internal_audit_tag" not in body["data"]
    # 确保我们刻意验证的"service 多余字段不漏出去"的逻辑被覆盖
    assert "feedback_id" in body["data"]


def test_post_feedback_ai_session_id_is_none(
    client_with_user: TestClient, patch_feedback_service: AsyncMock
) -> None:
    """PR-2 约束：当前 ``ai_session_id`` 始终为 ``None``（PR-2 未联动 AI 会话）。"""
    resp = client_with_user.post(
        "/api/v1/feedback",
        json={"feedback_type": "general"},
    )
    body = resp.json()
    assert body["data"]["ai_session_id"] is None


def test_post_feedback_ack_text_and_ack_match(
    client_with_user: TestClient, patch_feedback_service: AsyncMock
) -> None:
    """PR-2 约束：``ack_text`` 是 ``ack`` 的文本版；当前两者相等（PR-5 再分）。"""
    resp = client_with_user.post(
        "/api/v1/feedback",
        json={"feedback_type": "general"},
    )
    body = resp.json()
    assert body["data"]["ack"] == body["data"]["ack_text"]