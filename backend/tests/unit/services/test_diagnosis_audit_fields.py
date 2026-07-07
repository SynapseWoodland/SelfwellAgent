"""Unit tests for ``app.services.diagnosis_service.create_diagnosis`` audit fields。

真源：本次 audit 整改
- report.created_by = str(user.id)         （诊断发起人）
- report.last_updated_by = str(user.id)    （创建即更新）
- user.last_updated_by = str(user.id)      （user 侧 report_cache 刷新）
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.diagnosis_service import create_diagnosis


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _make_user(user_id: str | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or "u-diag-1"
    user.age_range = "23-28"
    user.focus_parts = ["shoulder_neck", "waist"]
    user.intensity = "适中"
    user.preferred_time = "晚"
    user.sitting_hours = "8-12h"
    user.report_cache = None
    user.report_cache_expires_at = None
    return user


def _valid_photos() -> list[dict]:
    return [
        {"url": "https://x/face.jpg", "body_part": "face", "format": "jpg", "size_bytes": 100},
        {"url": "https://x/head.jpg", "body_part": "head", "format": "jpg", "size_bytes": 100},
        {
            "url": "https://x/shoulder.jpg",
            "body_part": "shoulder_neck",
            "format": "jpg",
            "size_bytes": 100,
        },
    ]


@pytest.mark.asyncio
async def test_create_diagnosis_report_audit_fields_use_current_user_id() -> None:
    user_id = "u-diag-1"
    user = _make_user(user_id=user_id)
    session = AsyncMock()
    # 1st execute: select User
    session.execute.return_value = _scalar_result(user)
    session.add = MagicMock()
    session.flush = AsyncMock()

    # Mock _llm_diagnose 避免触发真实 LLM 调用
    fake_payload = {
        "directions": [{"title": "养护", "description": "...", "video_id": None}],
        "tags": ["颈肩"],
        "summary": "ok",
    }
    with patch(
        "app.services.diagnosis_service._llm_diagnose",
        new=AsyncMock(return_value=(fake_payload, Decimal("0.0"), "mock-llm")),
    ):
        await create_diagnosis(
            session, user_id=user_id, photos=_valid_photos(), complaint=None
        )

    report = session.add.call_args[0][0]
    forbidden = {"M2", "m2", "diagnosis", "system", "doctor"}
    assert report.created_by not in forbidden
    assert report.last_updated_by not in forbidden
    assert report.created_by == user_id
    assert report.last_updated_by == user_id

    # user.last_updated_by 也必须等于当前用户
    assert user.last_updated_by == user_id


@pytest.mark.asyncio
async def test_create_diagnosis_user_last_updated_by_is_current_user() -> None:
    """user.report_cache 刷新时，user.last_updated_by 必须 = 当前 user_id。"""
    user_id = "u-diag-2"
    user = _make_user(user_id=user_id)
    session = AsyncMock()
    session.execute.return_value = _scalar_result(user)
    session.add = MagicMock()
    session.flush = AsyncMock()

    fake_payload = {
        "directions": [{"title": "a", "description": "b", "video_id": None}],
        "tags": ["x"],
        "summary": "y",
    }
    with patch(
        "app.services.diagnosis_service._llm_diagnose",
        new=AsyncMock(return_value=(fake_payload, Decimal("0.0"), "mock")),
    ):
        await create_diagnosis(session, user_id=user_id, photos=_valid_photos())

    assert user.last_updated_by == user_id
    assert user.last_updated_by not in {"M2", "m2", "diagnosis", "system"}


@pytest.mark.asyncio
async def test_create_diagnosis_audit_time_is_utc() -> None:
    user_id = "u-1"
    user = _make_user(user_id=user_id)
    session = AsyncMock()
    session.execute.return_value = _scalar_result(user)
    session.add = MagicMock()
    session.flush = AsyncMock()

    fake_payload = {
        "directions": [{"title": "a", "description": "b", "video_id": None}],
        "tags": ["x"],
        "summary": "y",
    }
    with patch(
        "app.services.diagnosis_service._llm_diagnose",
        new=AsyncMock(return_value=(fake_payload, Decimal("0.0"), "mock")),
    ):
        before = datetime.now(UTC)
        await create_diagnosis(session, user_id=user_id, photos=_valid_photos())
        after = datetime.now(UTC)

    report = session.add.call_args[0][0]
    assert before <= report.created_time <= after
    assert before <= report.last_updated_time <= after
    assert report.created_time.tzinfo is not None
    assert report.created_time.utcoffset().total_seconds() == 0
