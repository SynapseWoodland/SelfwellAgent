"""Unit tests for ``app.services.plan_service.generate_plan`` audit fields。

真源：本次 audit 整改
- plan.created_by = str(user_id)
- plan.last_updated_by = str(user_id)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.plan_service import generate_plan


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_result(values: list) -> MagicMock:
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


def _make_report(report_id: str = "rpt-1", user_id: str = "u-1") -> MagicMock:
    r = MagicMock()
    r.id = report_id
    r.user_id = user_id
    r.tags = {"items": ["颈肩", "腰背"]}
    r.deleted_at = None
    return r


def _build_session(*, report, existing_plan=None, videos: list | None = None) -> AsyncMock:
    """完整跑通 generate_plan 的 fake session。

    execute 顺序：
    1. select Report (where id, user_id)
    2. select Plan (where user_id, status=active) — duplicate check
    3. select Video — list_active_videos
    """
    session = AsyncMock()
    session.execute.side_effect = [
        _scalar_result(report),
        _scalar_result(existing_plan),
        _scalars_result(videos or []),
    ]
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_generate_plan_audit_fields_use_current_user_id() -> None:
    """plan.created_by / last_updated_by 必须 = str(user_id)，不能是 "M3" 等业务代号。"""
    user_id = "01900000-0000-0000-0000-000000000099"
    report = _make_report(user_id=user_id)
    session = _build_session(report=report)

    await generate_plan(session, user_id=user_id, report_id="rpt-1", intensity="适中")

    plan = session.add.call_args[0][0]
    forbidden = {"M3", "m3", "plan", "system", "wx-login"}
    assert plan.created_by not in forbidden
    assert plan.last_updated_by not in forbidden
    assert plan.created_by == user_id
    assert plan.last_updated_by == user_id


@pytest.mark.asyncio
async def test_generate_plan_audit_fields_are_uuid_string() -> None:
    """Audit 字段必须是字符串（UUID），而不是 UUID 对象或 None。"""
    user_id = "u-abc-123"
    report = _make_report(user_id=user_id)
    session = _build_session(report=report)

    await generate_plan(session, user_id=user_id, report_id="rpt-1")

    plan = session.add.call_args[0][0]
    assert isinstance(plan.created_by, str)
    assert isinstance(plan.last_updated_by, str)
    assert plan.created_by  # 非空
    assert plan.last_updated_by  # 非空


@pytest.mark.asyncio
async def test_generate_plan_audit_time_is_utc() -> None:
    """created_time / last_updated_time 必须 = datetime.now(UTC)。"""
    from datetime import UTC, datetime

    user_id = "u-1"
    report = _make_report(user_id=user_id)
    session = _build_session(report=report)

    before = datetime.now(UTC)
    await generate_plan(session, user_id=user_id, report_id="rpt-1")
    after = datetime.now(UTC)

    plan = session.add.call_args[0][0]
    assert before <= plan.created_time <= after
    assert before <= plan.last_updated_time <= after
    assert plan.created_time.tzinfo is not None
    assert plan.created_time.utcoffset().total_seconds() == 0
