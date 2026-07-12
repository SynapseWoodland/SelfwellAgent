"""Unit tests for V2 IA PR-2 services（5 个 service 全覆盖）。

覆盖：
- ``app.services.v2.badge_service``
- ``app.services.v2.album_service``
- ``app.services.v2.archive_service``
- ``app.services.v2.notification_service``
- ``app.services.v2.support_service``

目标：每个 service 行覆盖率 ≥ 80%。
策略：unittest.mock.AsyncMock + MagicMock 注入 ORM 行为；不依赖真实 DB。
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# §共用辅助
# ═══════════════════════════════════════════════════════════════════════════════


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar_one.return_value = value
    return r


def _scalar_all_result(values):
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


def _scalar_dates_result(values):
    """模拟 ``result.all()`` 返回 [(date,), ...] 用于日期列表。"""
    r = MagicMock()
    r.all.return_value = [(d,) for d in values]
    return r


def _make_session(execute_returns=None, scalars_all=None) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    if scalars_all is not None:
        session.execute = AsyncMock(return_value=_scalar_all_result(scalars_all))
    elif execute_returns is not None:
        session.execute = AsyncMock(return_value=execute_returns)
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# §一 badge_service
# ═══════════════════════════════════════════════════════════════════════════════


class TestBadgeService:
    """``app.services.v2.badge_service`` 测试套件。"""

    def test_validate_code_valid(self) -> None:
        from app.db.models.user_badge import BADGE_CODES
        from app.services.v2.badge_service import _validate_code

        for code in BADGE_CODES:
            assert _validate_code(code) == code

    def test_validate_code_invalid_raises(self) -> None:
        from app.services.v2.badge_service import BadgeCodeError, _validate_code

        with pytest.raises(BadgeCodeError):
            _validate_code("not_a_real_badge")

    def test_validate_progress_negative_raises(self) -> None:
        from app.services.v2.badge_service import BadgeProgressError, _validate_progress

        with pytest.raises(BadgeProgressError):
            _validate_progress(-1, target=10)

    def test_validate_progress_overflow_raises(self) -> None:
        from app.services.v2.badge_service import BadgeProgressError, _validate_progress

        with pytest.raises(BadgeProgressError):
            _validate_progress(11, target=10)

    @pytest.mark.asyncio
    async def test_list_user_badges_empty_returns_empty_lists(self) -> None:
        from app.services.v2.badge_service import list_user_badges

        session = _make_session(scalars_all=[])
        result = await list_user_badges(session, user_id="u-1")
        assert result["unlocked"] == []
        assert result["in_progress"] == []
        assert result["total_unlocked"] == 0
        assert result["total_codes"] == 6

    @pytest.mark.asyncio
    async def test_list_user_badges_with_unlocked_and_in_progress(self) -> None:
        from app.db.models.user_badge import UserBadge
        from app.services.v2.badge_service import list_user_badges

        now = datetime.now(UTC)
        unlocked = UserBadge(
            id=uuid4(),
            user_id=uuid4(),
            code="streak_7",
            progress=7,
            target=7,
            unlocked_at=now,
            created_at=now,
            created_time=now,
            last_updated_time=now,
        )
        in_progress = UserBadge(
            id=uuid4(),
            user_id=uuid4(),
            code="streak_21",
            progress=5,
            target=30,
            unlocked_at=None,
            created_at=now,
            created_time=now,
            last_updated_time=now,
        )
        session = _make_session(scalars_all=[unlocked, in_progress])

        result = await list_user_badges(session, user_id="u-1")
        assert result["total_unlocked"] == 1
        assert result["total_codes"] == 6
        assert len(result["unlocked"]) == 1
        assert result["unlocked"][0]["code"] == "streak_7"
        assert result["unlocked"][0]["unlocked"] is True
        assert len(result["in_progress"]) == 1
        assert result["in_progress"][0]["code"] == "streak_21"

    @pytest.mark.asyncio
    async def test_increment_progress_creates_new(self) -> None:
        from app.services.v2.badge_service import increment_progress

        session = _make_session(execute_returns=_scalar_result(None))
        result = await increment_progress(
            session, user_id="u-1", code="streak_7", delta=1, target=7
        )
        assert result["code"] == "streak_7"
        assert result["progress"] == 1
        assert result["target"] == 7
        assert result["unlocked"] is False

    @pytest.mark.asyncio
    async def test_increment_progress_auto_unlocks(self) -> None:
        from app.db.models.user_badge import UserBadge
        from app.services.v2.badge_service import increment_progress

        existing = UserBadge(
            id=uuid4(),
            user_id=uuid4(),
            code="streak_7",
            progress=5,
            target=7,
            unlocked_at=None,
            created_at=datetime.now(UTC),
            created_time=datetime.now(UTC),
            last_updated_time=datetime.now(UTC),
        )
        session = _make_session(execute_returns=_scalar_result(existing))
        result = await increment_progress(
            session, user_id="u-1", code="streak_7", delta=2
        )
        assert result["progress"] == 7
        assert result["unlocked"] is True
        assert result["unlocked_at"] is not None

    @pytest.mark.asyncio
    async def test_increment_progress_invalid_delta_raises(self) -> None:
        from app.services.v2.badge_service import BadgeProgressError, increment_progress

        session = _make_session()
        with pytest.raises(BadgeProgressError):
            await increment_progress(
                session, user_id="u-1", code="streak_7", delta=0
            )

    @pytest.mark.asyncio
    async def test_increment_progress_first_create_without_target_raises(self) -> None:
        from app.services.v2.badge_service import BadgeProgressError, increment_progress

        session = _make_session(execute_returns=_scalar_result(None))
        with pytest.raises(BadgeProgressError):
            await increment_progress(
                session, user_id="u-1", code="streak_7", delta=1
            )

    @pytest.mark.asyncio
    async def test_unlock_badge_idempotent(self) -> None:
        from app.db.models.user_badge import UserBadge
        from app.services.v2.badge_service import unlock_badge

        now = datetime.now(UTC)
        existing = UserBadge(
            id=uuid4(),
            user_id=uuid4(),
            code="streak_7",
            progress=7,
            target=7,
            unlocked_at=now,
            created_at=now,
            created_time=now,
            last_updated_time=now,
        )
        session = _make_session(execute_returns=_scalar_result(existing))
        result = await unlock_badge(session, user_id="u-1", code="streak_7")
        assert result["unlocked"] is True

    @pytest.mark.asyncio
    async def test_unlock_badge_creates_when_missing(self) -> None:
        from app.services.v2.badge_service import unlock_badge

        session = _make_session(execute_returns=_scalar_result(None))
        result = await unlock_badge(session, user_id="u-1", code="streak_7")
        assert result["code"] == "streak_7"
        assert result["unlocked"] is True

    @pytest.mark.asyncio
    async def test_get_badges_summary_no_unlocked(self) -> None:
        from app.services.v2.badge_service import get_badges_summary

        session = _make_session(scalars_all=[])
        result = await get_badges_summary(session, user_id="u-1")
        assert result["total_unlocked"] == 0
        assert result["total_codes"] == 6
        assert result["latest_unlocked"] is None

    @pytest.mark.asyncio
    async def test_get_badges_summary_with_latest(self) -> None:
        from app.db.models.user_badge import UserBadge
        from app.services.v2.badge_service import get_badges_summary

        now = datetime.now(UTC)
        older = UserBadge(
            id=uuid4(),
            user_id=uuid4(),
            code="streak_7",
            progress=7,
            target=7,
            unlocked_at=now.replace(day=1),
            created_at=now,
            created_time=now,
            last_updated_time=now,
        )
        newer = UserBadge(
            id=uuid4(),
            user_id=uuid4(),
            code="streak_21",
            progress=30,
            target=30,
            unlocked_at=now,
            created_at=now,
            created_time=now,
            last_updated_time=now,
        )
        session = _make_session(scalars_all=[older, newer])
        result = await get_badges_summary(session, user_id="u-1")
        assert result["total_unlocked"] == 2
        assert result["latest_unlocked"]["code"] == "streak_21"


# ═══════════════════════════════════════════════════════════════════════════════
# §二 album_service
# ═══════════════════════════════════════════════════════════════════════════════


class TestAlbumService:
    """``app.services.v2.album_service`` 测试套件。"""

    def test_parse_week_valid(self) -> None:
        from app.services.v2.album_service import _parse_week

        assert _parse_week("2026-W01") == (2026, 1)
        assert _parse_week("2025-W52") == (2025, 52)

    def test_parse_week_invalid_raises(self) -> None:
        from app.services.v2.album_service import AlbumWeekFormatError, _parse_week

        with pytest.raises(AlbumWeekFormatError):
            _parse_week("2026-01")
        with pytest.raises(AlbumWeekFormatError):
            _parse_week("not-a-week")

    def test_week_range_returns_utc_datetimes(self) -> None:
        from app.services.v2.album_service import _week_range

        start, end = _week_range(2026, 1)
        assert end > start
        assert (end - start).days == 7

    @pytest.mark.asyncio
    async def test_list_album_photos_by_week_empty(self) -> None:
        from app.services.v2.album_service import list_album_photos_by_week

        session = _make_session(scalars_all=[])
        result = await list_album_photos_by_week(
            session, user_id="u-1", week="2026-W28"
        )
        assert result["week"] == "2026-W28"
        assert result["photos"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_list_album_photos_by_week_invalid_format(self) -> None:
        from app.services.v2.album_service import (
            AlbumWeekFormatError,
            list_album_photos_by_week,
        )

        session = _make_session()
        with pytest.raises(AlbumWeekFormatError):
            await list_album_photos_by_week(session, user_id="u-1", week="bad")

    @pytest.mark.asyncio
    async def test_get_album_stats_empty(self) -> None:
        from app.services.v2.album_service import get_album_stats

        # 4 executes: photos count, diary count, checkin dates, user.created_at
        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(0),
                _scalar_result(0),
                _scalar_result(0),
                _scalar_result(None),
            ]
        )
        result = await get_album_stats(session, user_id="u-1")
        assert result["total_photos"] == 0
        assert result["total_checkin_days"] == 0
        assert result["days_in_app"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# §三 archive_service
# ═══════════════════════════════════════════════════════════════════════════════


class TestArchiveService:
    """``app.services.v2.archive_service`` 测试套件。"""

    def test_stage_for_day_1(self) -> None:
        from app.services.v2.archive_service import _stage_for

        assert _stage_for(1) == "习惯启动"
        assert _stage_for(7) == "习惯启动"
        assert _stage_for(8) == "稳步提升"
        assert _stage_for(14) == "稳步提升"
        assert _stage_for(15) == "进阶养护"
        assert _stage_for(21) == "进阶养护"
        assert _stage_for(99) == "进阶养护"

    @pytest.mark.asyncio
    async def test_get_archive_summary_user_not_found(self) -> None:
        from app.services.v2.archive_service import ArchiveError, get_archive_summary

        session = _make_session(execute_returns=_scalar_result(None))
        with pytest.raises(ArchiveError):
            await get_archive_summary(session, user_id="u-missing")

    @pytest.mark.asyncio
    async def test_get_archive_summary_with_data(self) -> None:
        from app.db.models.user import User
        from app.services.v2.archive_service import get_archive_summary

        user = MagicMock(spec=User)
        user.id = "u-1"
        user.nickname = "tester"
        user.avatar = ""
        user.status = "active"

        # 第一个 execute 返回 user，第二个返回空 tags，第三个返回空 plan，
        # 第四个返回 checkin count，第五个返回 checkin dates
        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(user),
                _scalar_all_result([]),  # tags
                _scalar_result(None),  # plan
                _scalar_result(0),  # checkin count
                _scalar_dates_result([]),  # checkin dates
            ]
        )
        result = await get_archive_summary(session, user_id="u-1")
        assert result["profile"]["nickname"] == "tester"
        assert result["plan"] is None
        assert "archive_generated_at" in result


# ═══════════════════════════════════════════════════════════════════════════════
# §四 notification_service
# ═══════════════════════════════════════════════════════════════════════════════


class TestNotificationService:
    """``app.services.v2.notification_service`` 测试套件。"""

    def test_serialize_pref(self) -> None:
        from app.services.v2.notification_service import _serialize

        now = datetime.now(UTC)
        pref = MagicMock()
        pref.pref_key = "daily_checkin"
        pref.pref_value = {"enabled": True}
        pref.updated_at = now

        out = _serialize(pref)
        assert out["pref_key"] == "daily_checkin"
        assert out["pref_value"] == {"enabled": True}

    @pytest.mark.asyncio
    async def test_list_notification_prefs_empty(self) -> None:
        from app.services.v2.notification_service import list_notification_prefs

        session = _make_session(scalars_all=[])
        result = await list_notification_prefs(session, user_id="u-1")
        assert result["prefs"] == {}
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_notification_prefs_with_data(self) -> None:
        from app.db.models.user_notification_pref import UserNotificationPref
        from app.services.v2.notification_service import list_notification_prefs

        now = datetime.now(UTC)
        rows = [
            UserNotificationPref(
                user_id=uuid4(),
                pref_key="daily_checkin",
                pref_value={"enabled": True},
                updated_at=now,
                created_by="u-1",
                created_time=now,
                last_updated_time=now,
                last_updated_by="u-1",
            ),
            UserNotificationPref(
                user_id=uuid4(),
                pref_key="weekly_recall",
                pref_value={"enabled": False},
                updated_at=now,
                created_by="u-1",
                created_time=now,
                last_updated_time=now,
                last_updated_by="u-1",
            ),
        ]
        session = _make_session(scalars_all=rows)
        result = await list_notification_prefs(session, user_id="u-1")
        assert result["total"] == 2
        assert result["prefs"]["daily_checkin"]["enabled"] is True
        assert result["prefs"]["weekly_recall"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_notification_prefs_empty_skips(self) -> None:
        from app.services.v2.notification_service import update_notification_prefs

        session = _make_session()
        result = await update_notification_prefs(
            session, user_id="u-1", prefs={}
        )
        assert result["updated_keys"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_update_notification_prefs_invalid_key_raises(self) -> None:
        from app.services.v2.notification_service import (
            NotificationPrefError,
            update_notification_prefs,
        )

        session = _make_session(execute_returns=_scalar_result(None))
        with pytest.raises(NotificationPrefError):
            await update_notification_prefs(
                session,
                user_id="u-1",
                prefs={"not_a_real_key": {"enabled": True}},
            )

    @pytest.mark.asyncio
    async def test_seed_default_prefs_creates_missing(self) -> None:
        from app.services.v2.notification_service import seed_default_prefs

        # list 现有 prefs 返回空 → seed 应跑 6 个 pg_insert
        session = _make_session(scalars_all=[])
        result = await seed_default_prefs(session, user_id="u-1")
        assert len(result["seeded_keys"]) == 6
        # 每条 default key 都应触发一次 session.execute
        assert session.execute.await_count >= 6

    @pytest.mark.asyncio
    async def test_update_notification_prefs_update_existing(self) -> None:
        from app.db.models.user_notification_pref import UserNotificationPref
        from app.services.v2.notification_service import update_notification_prefs

        now = datetime.now(UTC)
        existing = UserNotificationPref(
            user_id=uuid4(),
            pref_key="daily_checkin",
            pref_value={"enabled": True},
            updated_at=now,
            created_by="u-1",
            created_time=now,
            last_updated_time=now,
            last_updated_by="u-1",
        )
        # 第一个 execute 是 pg_insert (无返回值)；第二个是 list (返回该 row)
        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[_scalar_result(None), _scalar_all_result([existing])]
        )
        result = await update_notification_prefs(
            session,
            user_id="u-1",
            prefs={"daily_checkin": {"enabled": False}},
        )
        assert "daily_checkin" in result["updated_keys"]
        assert result["total"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# §五 support_service
# ═══════════════════════════════════════════════════════════════════════════════


class TestSupportService:
    """``app.services.v2.support_service`` 测试套件。"""

    def test_list_faq_all(self) -> None:
        from app.services.v2.support_service import FAQ_LIST, list_faq

        out = list_faq()
        assert out["total"] == len(FAQ_LIST)
        assert len(out["faqs"]) == len(FAQ_LIST)
        assert len(out["categories"]) >= 1

    def test_list_faq_by_category(self) -> None:
        from app.services.v2.support_service import list_faq

        out = list_faq(category="打卡")
        for item in out["faqs"]:
            assert item["category"] == "打卡"

    @pytest.mark.asyncio
    async def test_request_data_export_returns_job(self) -> None:
        from app.services.v2.support_service import request_data_export

        session = _make_session(execute_returns=_scalar_result(None))
        result = await request_data_export(session, user_id="u-1")
        assert "job_id" in result
        assert result["status"] == "queued"

    @pytest.mark.asyncio
    async def test_request_account_deletion_creates(self) -> None:
        from app.services.v2.support_service import request_account_deletion

        session = _make_session(execute_returns=_scalar_result(None))
        result = await request_account_deletion(session, user_id="u-1")
        assert "deletion_id" in result
        assert result["status"] == "pending_cool_down"
        assert "cool_down_until" in result

    @pytest.mark.asyncio
    async def test_request_account_deletion_already_pending(self) -> None:
        from app.services.v2.support_service import (
            DeletionAlreadyPendingError,
            request_account_deletion,
        )

        existing = MagicMock()
        existing.status = "pending_cool_down"
        session = _make_session(execute_returns=_scalar_result(existing))
        with pytest.raises(DeletionAlreadyPendingError):
            await request_account_deletion(session, user_id="u-1")

    @pytest.mark.asyncio
    async def test_cancel_deletion_not_found(self) -> None:
        from app.services.v2.support_service import (
            DeletionNotFoundError,
            cancel_deletion,
        )

        session = _make_session(execute_returns=_scalar_result(None))
        with pytest.raises(DeletionNotFoundError):
            await cancel_deletion(
                session, user_id="u-1", deletion_id="d-missing"
            )

    @pytest.mark.asyncio
    async def test_cancel_deletion_success(self) -> None:
        from app.services.v2.support_service import cancel_deletion

        existing = MagicMock()
        existing.status = "pending_cool_down"
        session = _make_session(execute_returns=_scalar_result(existing))
        result = await cancel_deletion(
            session, user_id="u-1", deletion_id="d-1"
        )
        assert result["status"] == "cancelled"
        assert existing.status == "cancelled"


# ═══════════════════════════════════════════════════════════════════════════════
# §六 契约测试：V2 service 返回结构（PR-2 contract 锁）
# ═══════════════════════════════════════════════════════════════════════════════


class TestV2ContractShapes:
    """PR-2 契约锁：返回 dict 的字段集必须稳定。"""

    @pytest.mark.asyncio
    async def test_badge_contract(self) -> None:
        from app.services.v2.badge_service import list_user_badges

        session = _make_session(scalars_all=[])
        out = await list_user_badges(session, user_id="u-1")
        assert set(out.keys()) == {"unlocked", "in_progress", "total_unlocked", "total_codes"}

    @pytest.mark.asyncio
    async def test_album_photos_contract(self) -> None:
        from app.services.v2.album_service import list_album_photos_by_week

        session = _make_session(scalars_all=[])
        out = await list_album_photos_by_week(
            session, user_id="u-1", week="2026-W28"
        )
        assert set(out.keys()) == {"week", "photos", "count"}

    @pytest.mark.asyncio
    async def test_album_stats_contract(self) -> None:
        from app.services.v2.album_service import get_album_stats

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(0),
                _scalar_result(0),
                _scalar_result(0),
                _scalar_result(None),
            ]
        )
        out = await get_album_stats(session, user_id="u-1")
        assert "total_photos" in out
        assert "total_checkin_days" in out
        assert "days_in_app" in out

    @pytest.mark.asyncio
    async def test_archive_contract(self) -> None:
        from app.services.v2.archive_service import get_archive_summary

        user = MagicMock()
        user.id = "u-1"
        user.nickname = "n"
        user.avatar = ""
        user.status = "active"
        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(user),
                _scalar_all_result([]),
                _scalar_result(None),
                _scalar_result(0),
                _scalar_dates_result([]),
            ]
        )
        out = await get_archive_summary(session, user_id="u-1")
        assert set(out.keys()) >= {
            "profile",
            "tags",
            "plan",
            "checkin",
            "archive_generated_at",
        }

    @pytest.mark.asyncio
    async def test_notification_contract(self) -> None:
        from app.services.v2.notification_service import list_notification_prefs

        session = _make_session(scalars_all=[])
        out = await list_notification_prefs(session, user_id="u-1")
        assert set(out.keys()) == {"prefs", "total"}

    def test_faq_contract(self) -> None:
        from app.services.v2.support_service import list_faq

        out = list_faq()
        assert set(out.keys()) == {"faqs", "total", "categories"}
        assert out["faqs"][0]["id"]
        assert out["faqs"][0]["question"]
        assert out["faqs"][0]["answer"]
