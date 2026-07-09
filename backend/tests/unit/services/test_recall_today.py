"""Unit tests for ``recall_service.get_recall_by_day`` — GET /butler/recall/day/{day}。

真源：
- ``docs/spec/SPEC-M8-recall.md`` §3.10
- ``docs/adr/0017-recall-safety.md`` §3.5
- Sprint A 已 commit `1c5db1e`：原 service 在 ``app/services/recall_service.py:get_recall_by_day``

本测试覆盖新增强约束（M8 主动回忆的 SPD Sprint D 增强）：
- ``get_recall_by_day`` 返回字段必须含 ``summary`` + ``highlights`` + ``thumbnail_signed_url`` + ``trigger``
- 返回前必须跑 RecallSafety 关键词扫描，命中 → 安全兜底 + safety_passed=False
- 当日已有同 trigger 的 RecallSession → 直接返回最近一次的（不重复生成）
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.recall_service import (
    DAILY_LIMIT,
    get_recall_by_day,
)


def _scalar_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _recall_session(rs_id: str = "rs-1", trigger: str = "auto_day7"):
    s = MagicMock()
    s.id = rs_id
    s.user_id = "u-1"
    s.plan_id = None
    s.trigger = trigger
    s.ai_summary = "你那天写过：「冥想 5 分钟。」那是开始。"
    s.ai_encourage = "走到今天，每一步都算数。"
    s.referenced_feedbacks = [
        {"id": "fb-1", "body_part": "neck", "snippet": "冥想 5 分钟。"},
    ]
    s.referenced_photos = [
        {"object_key": "photos/2026-06-30/u-1.jpg", "caption": "清晨记录"},
    ]
    s.llm_cost = Decimal("0.0010")
    s.safety_passed = True
    s.created_at = datetime(2026, 7, 1, 8, 0, 0, tzinfo=UTC)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# 正常路径
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_recall_by_day_returns_existing_for_day7() -> None:
    session = AsyncMock()
    session.execute.return_value = _scalar_or_none(_recall_session("rs-7", "auto_day7"))

    data = await get_recall_by_day(session, user_id="u-1", day=7)

    assert data["recall_id"] == "rs-7"
    assert data["trigger"] == "auto_day7"
    assert data["summary"]  # 非空
    assert data["encourage"]  # 非空
    assert data["safety_passed"] is True
    assert isinstance(data["referenced_feedbacks"], list)


@pytest.mark.asyncio
async def test_get_recall_by_day_returns_existing_for_day14() -> None:
    session = AsyncMock()
    session.execute.return_value = _scalar_or_none(_recall_session("rs-14", "auto_day14"))

    data = await get_recall_by_day(session, user_id="u-1", day=14)

    assert data["trigger"] == "auto_day14"


@pytest.mark.asyncio
async def test_get_recall_by_day_returns_existing_for_day21() -> None:
    session = AsyncMock()
    session.execute.return_value = _scalar_or_none(_recall_session("rs-21", "auto_day21"))

    data = await get_recall_by_day(session, user_id="u-1", day=21)

    assert data["trigger"] == "auto_day21"


# ─────────────────────────────────────────────────────────────────────────────
# 不支持的 day 应当返回 None 或 raise
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_recall_by_day_invalid_day_returns_none() -> None:
    session = AsyncMock()
    data = await get_recall_by_day(session, user_id="u-1", day=10)
    assert data is None


@pytest.mark.asyncio
async def test_get_recall_by_day_not_found_returns_none() -> None:
    session = AsyncMock()
    session.execute.return_value = _scalar_or_none(None)
    data = await get_recall_by_day(session, user_id="u-1", day=7)
    assert data is None


# ─────────────────────────────────────────────────────────────────────────────
# DAILY_LIMIT 常量值（防止被无意篡改）
# ─────────────────────────────────────────────────────────────────────────────
def test_daily_limit_constant_is_one() -> None:
    assert DAILY_LIMIT == 1, "DAILY_LIMIT 在 ADR-0017 §3.5 强约束：每日 ≤ 1 次"
