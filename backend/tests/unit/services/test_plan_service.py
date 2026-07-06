"""Unit tests for plan_service (generate_plan with mock session)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.plan_service import (
    PLAN_LENGTH_DAYS,
    _phase_for_day,
    _phase_tasks,
    generate_plan,
    list_active_videos,
)


def test_phase_for_day() -> None:
    assert _phase_for_day(1) == 1
    assert _phase_for_day(7) == 1
    assert _phase_for_day(8) == 2
    assert _phase_for_day(14) == 2
    assert _phase_for_day(15) == 3
    assert _phase_for_day(21) == 3


def test_phase_tasks() -> None:
    assert _phase_tasks(1) == 1
    assert _phase_tasks(8) == 2
    assert _phase_tasks(15) == 3


@pytest.mark.asyncio
async def test_list_active_videos_empty() -> None:
    fake_session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    fake_session.execute.return_value = result
    videos = await list_active_videos(fake_session)
    assert videos == []


@pytest.mark.asyncio
async def test_generate_plan_insufficient_videos_uses_standard() -> None:
    """视频库 < 50 时走标准模板路径。"""
    from uuid import uuid4

    fake_session = AsyncMock()
    user_id = str(uuid4())
    report_id = str(uuid4())

    # 1st: load report
    rpt = SimpleNamespace(
        id=report_id,
        user_id=user_id,
        tags={"items": ["face", "head"]},
        directions={},
        deleted_at=None,
    )
    rpt_result = MagicMock()
    rpt_result.scalar_one_or_none.return_value = rpt

    # 2nd: check existing plan
    exist_result = MagicMock()
    exist_result.scalar_one_or_none.return_value = None

    # 3rd: list active videos (empty)
    videos_result = MagicMock()
    videos_result.scalars.return_value.all.return_value = []

    fake_session.execute.side_effect = [rpt_result, exist_result, videos_result]
    fake_session.flush = AsyncMock()
    fake_session.add = MagicMock()

    result = await generate_plan(fake_session, user_id=user_id, report_id=report_id)
    assert result["length_days"] == PLAN_LENGTH_DAYS
    assert len(result["days"]) == 21
    # 每个 day 的 tasks 数量符合阶段配比
    for d in result["days"][:7]:
        assert len(d["tasks"]) == 1
    for d in result["days"][7:14]:
        assert len(d["tasks"]) == 2
    for d in result["days"][14:21]:
        assert len(d["tasks"]) == 3


@pytest.mark.asyncio
async def test_generate_plan_no_report_raises() -> None:
    from app.services.plan_service import PlanNoReportError

    fake_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = result
    with pytest.raises(PlanNoReportError):
        await generate_plan(fake_session, user_id="x", report_id="y")
