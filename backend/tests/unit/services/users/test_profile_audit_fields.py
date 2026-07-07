"""Unit tests for ``app.services.users.profile_service.update_user_profile`` audit fields。

真源：本次 audit 整改
- user.last_updated_by = user_id  （改自己档案的人）
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.users.profile_service import update_user_profile


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _make_user(user_id: str = "u-profile-1", status: str = "draft") -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.status = status
    u.age_range = None
    u.focus_parts = None
    u.intensity = None
    u.preferred_time = None
    u.sitting_hours = None
    return u


@pytest.mark.asyncio
async def test_update_user_profile_last_updated_by_is_current_user() -> None:
    """user.last_updated_by 必须 = 当前 user_id，不能是 "profile-update"。"""
    user_id = "u-1"
    user = _make_user(user_id=user_id, status="active")
    session = AsyncMock()
    session.execute.return_value = _scalar_result(user)
    session.flush = AsyncMock()

    await update_user_profile(
        session, user_id=user_id, payload={"age_range": "23-28"}
    )

    forbidden = {"profile-update", "M1", "m1", "system", ""}
    assert user.last_updated_by not in forbidden
    assert user.last_updated_by == user_id


@pytest.mark.asyncio
async def test_update_user_profile_audit_time_is_utc() -> None:
    user_id = "u-1"
    user = _make_user(user_id=user_id, status="active")
    session = AsyncMock()
    session.execute.return_value = _scalar_result(user)
    session.flush = AsyncMock()

    before = datetime.now(UTC)
    await update_user_profile(session, user_id=user_id, payload={"age_range": "23-28"})
    after = datetime.now(UTC)

    assert before <= user.last_updated_time <= after
    assert user.last_updated_time.tzinfo is not None
    assert user.last_updated_time.utcoffset().total_seconds() == 0


@pytest.mark.asyncio
async def test_update_user_profile_audit_on_draft_promotion() -> None:
    """首登补全 draft → active 时，audit 字段仍然归属当前用户。"""
    user_id = "u-draft-1"
    user = _make_user(user_id=user_id, status="draft")
    session = AsyncMock()
    session.execute.return_value = _scalar_result(user)
    session.flush = AsyncMock()

    # 一次性补齐 5 字段 → 触发 draft → active
    await update_user_profile(
        session,
        user_id=user_id,
        payload={
            "age_range": "23-28",
            "focus_parts": ["shoulder_neck"],
            "intensity": "适中",
            "preferred_time": "晚",
            "sitting_hours": "8-12h",
        },
    )

    assert user.status == "active"
    assert user.last_updated_by == user_id
