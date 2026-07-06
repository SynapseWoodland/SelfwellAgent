"""Unit tests for ``app.services.users.draft_promotion``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.users.draft_promotion import (
    DRAFT_TTL_HOURS,
    promote_due_drafts,
)


def _make_user(*, created_hours_ago: float, status: str = "draft") -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.status = status
    user.created_at = datetime.now(UTC) - timedelta(hours=created_hours_ago)
    user.last_updated_time = None
    user.last_updated_by = ""
    return user


@pytest.mark.asyncio
async def test_promote_due_drafts_promotes_24h_old() -> None:
    user_24h = _make_user(created_hours_ago=DRAFT_TTL_HOURS + 1)
    user_2h = _make_user(created_hours_ago=2)
    fake_session = AsyncMock()

    # 1st execute: SELECT draft users
    first_result = MagicMock()
    first_result.scalars.return_value.all.return_value = [user_24h, user_2h]
    # 2nd execute (per user): SELECT feedback
    fb_result = MagicMock()
    fb_result.scalar_one_or_none.return_value = None
    fake_session.execute.side_effect = [first_result, fb_result, fb_result]
    fake_session.flush = AsyncMock()

    promoted = await promote_due_drafts(fake_session)
    assert promoted == 1
    assert user_24h.status == "active"
    assert user_2h.status == "draft"


@pytest.mark.asyncio
async def test_promote_due_drafts_empty() -> None:
    fake_session = AsyncMock()
    first_result = MagicMock()
    first_result.scalars.return_value.all.return_value = []
    fake_session.execute.return_value = first_result
    fake_session.flush = AsyncMock()
    promoted = await promote_due_drafts(fake_session)
    assert promoted == 0
