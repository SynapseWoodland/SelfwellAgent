"""Unit tests for ``app.services.checkin_service`` audit fields。

真源：本次 audit 字段整改（详见 docs/refactor-history）。
- checkin.created_by = str(user.id)
- checkin.last_updated_by = str(user.id)
- user.last_updated_by = str(user.id) （打卡时同步刷新）

业务行为不变，仅验证 audit 字段取值。
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.checkin_service import create_checkin


def _make_user(user_id: str | None = None) -> MagicMock:
    user = MagicMock()
    user.id = uuid4() if user_id is None else user_id
    user.report_cache = None
    return user


def _make_plan(plan_id: str = "plan-1", days_items: list[dict] | None = None) -> MagicMock:
    plan = MagicMock()
    plan.id = plan_id
    plan.user_id = "u-1"
    plan.days = {
        "items": days_items
        if days_items is not None
        else [{"day": 1, "tasks": [{"video_id": "v-1"}]}]
    }
    plan.deleted_at = None
    return plan


def _build_session_with(user: MagicMock, plan: MagicMock, dup_existing: bool = False) -> AsyncMock:
    """构造能跑通 create_checkin 完整路径的 fake session。"""
    fake_session = AsyncMock()
    # 3 次 execute：_find_user, _find_plan, dup check
    exec_results = [
        _scalar_result(user),       # _find_user
        _scalar_result(plan),       # _find_plan
        _scalar_result(MagicMock() if dup_existing else None),  # dup check
    ]
    fake_session.execute.side_effect = exec_results
    fake_session.flush = AsyncMock()
    # 捕获 session.add 写入的 Checkin 对象
    fake_session.add = MagicMock()
    return fake_session


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_create_checkin_audit_fields_use_current_user_id() -> None:
    """created_by / last_updated_by 必须 = str(user.id)，不能是 "M4" 等业务代号。"""
    user = _make_user()
    plan = _make_plan()
    session = _build_session_with(user, plan)

    await create_checkin(
        session,
        user_id=str(user.id),
        plan_id=plan.id,
        day=1,
        video_id="v-1",
        feeling="还不错",
    )

    # 找到 session.add 写入的 Checkin 对象
    assert session.add.called
    checkin = session.add.call_args[0][0]

    # 业务代号 / 死字面量 全部禁止
    forbidden = {"M4", "m4", "checkin", "system", "wx-login"}
    assert checkin.created_by not in forbidden
    assert checkin.last_updated_by not in forbidden

    # 必须等于当前用户 ID
    assert checkin.created_by == str(user.id)
    assert checkin.last_updated_by == str(user.id)
    # 同时刷新 user.last_updated_by
    assert user.last_updated_by == str(user.id)


@pytest.mark.asyncio
async def test_create_checkin_audit_time_is_utc() -> None:
    """created_time / last_updated_time 必须 = datetime.now(UTC)。"""
    user = _make_user()
    plan = _make_plan()
    session = _build_session_with(user, plan)

    before = datetime.now(UTC)
    await create_checkin(
        session,
        user_id=str(user.id),
        plan_id=plan.id,
        day=1,
        video_id="v-1",
    )
    after = datetime.now(UTC)

    checkin = session.add.call_args[0][0]
    assert before <= checkin.created_time <= after
    assert before <= checkin.last_updated_time <= after
    # tzinfo 必须是 UTC
    assert checkin.created_time.tzinfo is not None
    assert checkin.created_time.utcoffset().total_seconds() == 0


@pytest.mark.asyncio
async def test_create_checkin_audit_differs_from_business_timestamp() -> None:
    """created_time（审计时间戳）必须 == created_at（业务时间戳），但二者语义不同。

    业务时间戳 created_at 是这条打卡记录的业务发生时刻 = 用户点按钮的时刻。
    审计时间戳 created_time 是 DB 行 INSERT 的时刻 = 同一时刻。
    验证两者一致但都是 UTC。
    """
    user = _make_user()
    plan = _make_plan()
    session = _build_session_with(user, plan)

    await create_checkin(
        session,
        user_id=str(user.id),
        plan_id=plan.id,
        day=1,
        video_id="v-1",
    )

    checkin = session.add.call_args[0][0]
    assert checkin.created_at == checkin.created_time
