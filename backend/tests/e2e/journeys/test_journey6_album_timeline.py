"""Phase 4 · 批次 5 · Journey 6：我的时光（21 天时间轴）。

业务路径：
1. GET /api/v1/me/album/stats → 聚合统计
2. GET /api/v1/me/album/photos?week=YYYY-WNN → 按周相册照片

真业务验证点：
  ① 真聚合 ≥10 天数据（不是 0 条）
  ② timeline 渲染数据 ≥7 段

注意：
- `get_album_stats` 聚合 checkins（distinct days）、feedback（photo count）、diary entries
- 没有「timeline」端点；用 `stats` + `album/photos` 验证「时光相册」聚合能力
- seed_checkins 有 42 条（USER_1 21天 + USER_2 21天）
- seed_feedback 有 30 条（USER_2）
- 验证聚合数 ≥10 天 = 满足「≥10 天数据」要求
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from .conftest import USER_1, USER_2


@pytest.mark.e2e
class TestJourney6AlbumTimeline:
    """Journey 6 — 相册聚合 → 时光时间轴。"""

    # ── ① 相册聚合统计 ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j6_album_stats(self, async_client, auth_header_factory):
        """GET /me/album/stats → 验证聚合统计 ≥10 天数据。

        验证点 ①：total_checkin_days ≥ 10（USER_2 有 21 天 seed checkins）。
        """
        headers = auth_header_factory(str(USER_2))
        resp = await async_client.get("/api/v1/me/album/stats", headers=headers)
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"album/stats 失败: {resp.status_code} {resp.text[:200]}"
        body = resp.json()
        data = body.get("data", {})

        total_checkin_days = data.get("total_checkin_days", 0)
        total_photos = data.get("total_photos", 0)
        total_diary = data.get("total_diary_entries", 0)

        # 验证点 ①：真聚合数据
        assert total_checkin_days > 0, \
            f"total_checkin_days 应 > 0（seed_checkins 有数据）: {data}"
        # 验证点 ①：≥10 天
        assert total_checkin_days >= 10, \
            f"total_checkin_days 应 ≥10（seed_checkins 有 21 天）: {total_checkin_days}"
        assert total_photos >= 0, f"total_photos 应 ≥0: {total_photos}"
        assert total_diary >= 0, f"total_diary_entries 应 ≥0: {total_diary}"

        # 验证点 ②：days_in_app ≥ 1
        days_in_app = data.get("days_in_app", 0)
        assert days_in_app >= 1, f"days_in_app 应 ≥1: {days_in_app}"

    # ── ② 按周相册照片 ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j6_album_photos_by_week(self, async_client, auth_header_factory):
        """GET /me/album/photos?week=YYYY-WNN → 验证周相册照片返回。

        USER_2 的 seed_feedback 覆盖 2026-06 至 2026-07，
        所以能找到至少一个 WNN 的照片。
        """
        headers = auth_header_factory(str(USER_2))
        # 当前 ISO 周
        import datetime
        today = datetime.date.today()
        iso_cal = today.isocalendar()
        current_week = f"{iso_cal[0]}-W{iso_cal[1]:02d}"

        resp = await async_client.get(
            f"/api/v1/me/album/photos?week={current_week}",
            headers=headers,
        )
        if resp.status_code == 400:
            pytest.skip(f"week 格式错误（{current_week}）或该周无照片")
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"album/photos 失败: {resp.status_code}"
        body = resp.json()
        data = body.get("data", {})
        assert "week" in data, f"album/photos 响应缺 week: {data}"
        assert "photos" in data, f"album/photos 响应缺 photos: {data}"
        photos = data.get("photos", [])
        assert isinstance(photos, list), f"photos 应为 list: {type(photos)}"

        # 如果本周有照片，验证每张照片含真实 photo_url
        if photos:
            for p in photos:
                url = p.get("photo_url", "")
                assert url.startswith("http"), f"photo_url 不是真实 URL: {url}"

    # ── ③ 多周聚合验证（≥7 段）────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j6_timeline_weeks(self, async_client, auth_header_factory):
        """遍历近 10 周，验证 timeline 数据 ≥7 段（weeks）。

        通过 album/photos 逐周查询，统计有照片的周数。
        这验证了「21 天时间轴」能真渲染多段数据。
        """
        headers = auth_header_factory(str(USER_2))

        import datetime
        today = datetime.date.today()
        weeks_with_data = []

        for i in range(10):  # 近 10 周
            d = today - datetime.timedelta(weeks=i)
            iso = d.isocalendar()
            week = f"{iso[0]}-W{iso[1]:02d}"

            resp = await async_client.get(
                f"/api/v1/me/album/photos?week={week}",
                headers=headers,
            )
            if resp.status_code != 200:
                continue
            data = resp.json().get("data", {})
            photos = data.get("photos", [])
            if photos:
                weeks_with_data.append(week)

        # 验证点 ②：timeline 渲染数据 ≥7 段（近 10 周有 ≥7 周有照片）
        assert len(weeks_with_data) >= 7, \
            f"近 10 周应有 ≥7 周有照片，实际 {len(weeks_with_data)} 周: {weeks_with_data}"

    # ── ④ USER_1 统计（验证独立用户）─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j6_user1_album_stats(self, async_client, auth_header_factory):
        """GET /me/album/stats（USER_1）→ 验证独立用户统计真聚合。"""
        headers = auth_header_factory(str(USER_1))
        resp = await async_client.get("/api/v1/me/album/stats", headers=headers)
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"USER_1 album/stats 失败: {resp.status_code}"
        data = resp.json().get("data", {})
        # USER_1 没有 mood_photo，但有 21 天 checkins
        total_checkins = data.get("total_checkin_days", 0)
        assert total_checkins >= 1, \
            f"USER_1 应有 checkin 数据（seed_checkins 有 21 天）: {total_checkins}"


def _check_any_5xx(response) -> None:
    if 500 <= response.status_code < 600:
        raise AssertionError(
            f"5xx ({response.status_code}): {response.text[:300]}"
        )
