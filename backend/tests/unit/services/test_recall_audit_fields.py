"""Unit tests for ``app.services.recall_service.generate_recall`` audit fields。

真源：本次 audit 整改
- RecallSession.created_by = str(user_id)
- RecallSession.last_updated_by = str(user_id)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.recall_service import generate_recall


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_result(values: list) -> MagicMock:
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


@pytest.mark.asyncio
async def test_generate_recall_audit_fields_use_current_user_id() -> None:
    user_id = "u-recall-1"
    session = AsyncMock()
    # execute 调用顺序：
    # 1. daily limit check (RecallSession)
    # 2. _load_referenced_feedbacks (Feedback)
    session.execute.side_effect = [
        _scalars_result([]),     # daily limit: empty
        _scalars_result([]),     # _load_referenced_feedbacks: empty (但 trigger=auto_day7 不要求)
    ]
    session.flush = AsyncMock()
    session.add = MagicMock()

    await generate_recall(session, user_id=user_id, trigger="auto_day7", plan_id="plan-1")

    rs = session.add.call_args[0][0]
    forbidden = {"M8", "m8", "recall", "system"}
    assert rs.created_by not in forbidden
    assert rs.last_updated_by not in forbidden
    assert rs.created_by == user_id
    assert rs.last_updated_by == user_id


@pytest.mark.asyncio
async def test_generate_recall_audit_time_is_utc() -> None:
    user_id = "u-1"
    session = AsyncMock()
    session.execute.side_effect = [_scalars_result([]), _scalars_result([])]
    session.flush = AsyncMock()
    session.add = MagicMock()

    before = datetime.now(UTC)
    await generate_recall(session, user_id=user_id, trigger="auto_day7", plan_id="p-1")
    after = datetime.now(UTC)

    rs = session.add.call_args[0][0]
    assert before <= rs.created_time <= after
    assert before <= rs.last_updated_time <= after
    assert rs.created_time.tzinfo is not None
    assert rs.created_time.utcoffset().total_seconds() == 0


@pytest.mark.asyncio
async def test_generate_recall_with_referenced_feedback_uses_current_user_id() -> None:
    """即使有 referenced feedbacks，audit 字段仍要归属到调用者 user_id。"""
    user_id = "u-real-1"
    fb_mock = MagicMock()
    fb_mock.id = "fb-1"
    fb_mock.body_part = "shoulder_neck"
    fb_mock.text_content = "今天颈肩有点僵"
    fb_mock.feedback_type = "text"
    fb_mock.created_time = datetime.now(UTC)
    fb_mock.created_by = user_id

    session = AsyncMock()
    session.execute.side_effect = [
        _scalars_result([]),         # daily limit
        _scalars_result([fb_mock]),  # _load_referenced_feedbacks
    ]
    session.flush = AsyncMock()
    session.add = MagicMock()

    await generate_recall(session, user_id=user_id, trigger="user_manual")

    rs = session.add.call_args[0][0]
    assert rs.created_by == user_id
    assert rs.last_updated_by == user_id
