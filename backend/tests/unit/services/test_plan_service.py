"""Unit tests for plan_service (generate_plan with mock session)."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.plan_service import (
    PLAN_LENGTH_DAYS,
    _phase_for_day,
    _phase_tasks,
    aggregate_plan_weeks,
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


# ─────────────────────────────────────────────────────────────────────────────
# aggregate_plan_weeks
# ─────────────────────────────────────────────────────────────────────────────


def _make_plan(started_at: date | None, tasks_per_day: int = 1) -> MagicMock:
    days: list[dict[str, object]] = []
    for d in range(1, PLAN_LENGTH_DAYS + 1):
        phase = 1 if d <= 7 else (2 if d <= 14 else 3)
        days.append(
            {
                "day": d,
                "phase": phase,
                "tasks": [{"video_id": f"v-{d}-{i}"} for i in range(tasks_per_day)],
            }
        )
    plan = MagicMock()
    plan.started_at = started_at
    plan.days = {"items": days}
    return plan


def test_aggregate_plan_weeks_returns_three_weeks() -> None:
    plan = _make_plan(date(2026, 7, 8))
    weeks = aggregate_plan_weeks(plan, today=date(2026, 7, 8))
    assert len(weeks) == 3
    titles = [w["title"] for w in weeks]
    assert titles == [
        "第一阶段 · 习惯启动",
        "第二阶段 · 强化提升",
        "第三阶段 · 稳定养成",
    ]
    assert [w["week_no"] for w in weeks] == [1, 2, 3]
    for w in weeks:
        assert len(w["days"]) == 7
        assert [d["day"] for d in w["days"]] == list(
            range((w["week_no"] - 1) * 7 + 1, w["week_no"] * 7 + 1)
        )


def test_aggregate_plan_weeks_today_state_correct() -> None:
    started = date(2026, 7, 8)
    today = date(2026, 7, 10)  # day 3
    plan = _make_plan(started)
    weeks = aggregate_plan_weeks(plan, today=today)
    flat = [d for w in weeks for d in w["days"]]
    by_day = {d["day"]: d["state"] for d in flat}
    assert by_day[1] == "done"
    assert by_day[2] == "done"
    assert by_day[3] == "today"
    assert by_day[4] == "locked"
    assert by_day[21] == "locked"
    assert by_day[3] == "today"


def test_aggregate_plan_weeks_done_state_for_past_days() -> None:
    started = date(2026, 7, 1)
    today = date(2026, 7, 8)  # day 8
    plan = _make_plan(started)
    weeks = aggregate_plan_weeks(plan, today=today)
    flat = [d for w in weeks for d in w["days"]]
    for d in flat[:7]:
        assert d["state"] == "done", d
    assert flat[7]["state"] == "today"


def test_aggregate_plan_weeks_locked_state_for_future_days() -> None:
    started = date(2026, 7, 8)
    today = date(2026, 7, 8)  # day 1
    plan = _make_plan(started)
    weeks = aggregate_plan_weeks(plan, today=today)
    flat = [d for w in weeks for d in w["days"]]
    assert flat[0]["state"] == "today"
    for d in flat[1:]:
        assert d["state"] == "locked", d


def test_aggregate_plan_weeks_handles_plan_at_day_1() -> None:
    started = date(2026, 7, 8)
    today = date(2026, 7, 8)
    plan = _make_plan(started)
    weeks = aggregate_plan_weeks(plan, today=today)
    flat = [d for w in weeks for d in w["days"]]
    assert flat[0]["day"] == 1
    assert flat[0]["state"] == "today"
    assert flat[-1]["day"] == 21
    assert flat[-1]["state"] == "locked"


def test_aggregate_plan_weeks_handles_plan_at_day_21() -> None:
    started = date(2026, 7, 8)
    today = started + timedelta(days=20)  # day 21
    plan = _make_plan(started)
    weeks = aggregate_plan_weeks(plan, today=today)
    flat = [d for w in weeks for d in w["days"]]
    for d in flat[:-1]:
        assert d["state"] == "done"
    assert flat[-1]["day"] == 21
    assert flat[-1]["state"] == "today"


def test_aggregate_plan_weeks_tasks_count_and_phase() -> None:
    started = date(2026, 7, 8)
    today = started + timedelta(days=10)
    plan = _make_plan(started, tasks_per_day=2)
    weeks = aggregate_plan_weeks(plan, today=today)
    for w in weeks:
        for d in w["days"]:
            assert d["tasks_count"] == 2
            assert d["phase"] in (1, 2, 3)
            if d["day"] <= 7:
                assert d["phase"] == 1
            elif d["day"] <= 14:
                assert d["phase"] == 2
            else:
                assert d["phase"] == 3


def test_aggregate_plan_weeks_does_not_mutate_plan() -> None:
    plan = _make_plan(date(2026, 7, 8))
    snapshot_items = list(plan.days["items"])
    aggregate_plan_weeks(plan, today=date(2026, 7, 10))
    assert plan.days["items"] == snapshot_items
    assert plan.started_at == date(2026, 7, 8)
