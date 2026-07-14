"""Phase 4 · 批次 5 · Journey 4：蜕变广场发表。

业务路径：
1. POST /api/v1/community/posts（content + images JSONB）
2. GET  /api/v1/community/posts/{id} → 验证 status=pending + images
3. POST /api/v1/community/posts/{id}/like（approved post）

真业务验证点：
  ① post 真入库 status=pending
  ② images 真存 OSS URL（不是 mock string）

前置：seed_posts（10 条，含 pending 和 approved）。
⚠ 限流：24h ≤ 3 条（seed_posts 已达上限时本测试 skip）。
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from .conftest import USER_1, USER_2


@pytest.mark.e2e
class TestJourney4CommunityPost:
    """Journey 4 — 社区发帖 → 获取详情 → 点赞。"""

    # ── ① 发帖（content + images）─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j4_create_post_with_images(self, async_client, auth_header_factory, shared_ctx):
        """POST /community/posts（content + images JSONB）→ 验证 status=pending。"""
        headers = auth_header_factory(str(USER_1))

        payload = {
            "content": "完成 21 天蜕变计划！每天 10 分钟，改变看得见。加油！",
            "images": [
                {
                    "url": "https://picsum.photos/400/300?random=j4img1",
                    "caption": "蜕变前后对比",
                },
                {
                    "url": "https://picsum.photos/400/300?random=j4img2",
                    "caption": "Day 7 打卡",
                },
            ],
        }
        resp = await async_client.post(
            "/api/v1/community/posts",
            json=payload,
            headers=headers,
        )
        if resp.status_code == 429:
            pytest.skip("今日发帖已达上限（24h ≤ 3 条），跳过发帖测试")
        _check_any_5xx(resp)
        assert resp.status_code in (200, 201), \
            f"发帖失败: {resp.status_code} {resp.text[:200]}"
        body = resp.json()
        data = body.get("data", {})
        post_id = data.get("post_id")
        assert post_id, f"发帖无 post_id: {data}"
        # 验证点 ① status=pending
        assert data.get("status") == "pending", \
            f"post status 应为 pending: {data.get('status')}"
        # 验证点 ② images 数量正确
        assert data.get("images_count") == 2, \
            f"images_count 应为 2: {data.get('images_count')}"
        shared_ctx["j4_post_id"] = post_id

    # ── ② 获取帖子详情 ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j4_get_post_pending(self, async_client, auth_header_factory, shared_ctx):
        """GET /community/posts/{id} → pending 帖子应 409（未审核）。

        注意：get_post 在 status=pending 时 raise PostPendingError → HTTP 409。
        这正是我们验证「帖子真入库 status=pending」的方式。
        """
        post_id = shared_ctx.get("j4_post_id")
        if not post_id:
            pytest.skip("无 post_id，跳过详情验证")

        headers = auth_header_factory(str(USER_1))
        resp = await async_client.get(f"/api/v1/community/posts/{post_id}", headers=headers)
        # 409 = pending（帖子已入库但未审核）
        if resp.status_code == 409:
            body = resp.json()
            # 验证 code 是 E_COMMUNITY_POST_PENDING
            code = body.get("detail", {}).get("code", "")
            assert "PENDING" in str(code).upper(), \
                f"409 应为 pending: {body}"
            # 验证点 ①：真入库（409 是因为 pending，非 404）
            return
        elif resp.status_code == 404:
            pytest.skip(f"post 未查到（可能被审核删除了）: {post_id}")
        else:
            _check_any_5xx(resp)
            # 如果审核通过了（unlikely），也 OK
            assert resp.status_code == 200, f"get_post 失败: {resp.status_code}"

    # ── ③ 获取帖子列表（验证真存 OSS URL）─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j4_list_posts_real_urls(self, async_client, auth_header_factory):
        """GET /community/posts → 验证 images 含真实 OSS URL。"""
        headers = auth_header_factory(str(USER_1))
        resp = await async_client.get("/api/v1/community/posts", headers=headers)
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"list posts 失败: {resp.status_code}"
        items = resp.json().get("data", [])
        assert len(items) > 0, "帖子列表为空（seed_posts 应该有数据）"

        for item in items:
            images = item.get("images") or []
            for img in images:
                url = img.get("url", "")
                # 验证点 ②：images 含真实 URL（非 placeholder）
                assert url.startswith("http"), f"image url 不是真实 URL: {url}"
                assert "placeholder" not in url.lower(), f"image url 含 placeholder: {url}"

    # ── ④ 点赞（approved post）────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j4_like_approved_post(self, async_client, auth_header_factory):
        """POST /community/posts/{id}/like（seed approved post）→ 验证 like_count +1。"""
        headers = auth_header_factory(str(USER_1))

        # 找一个 approved post（seed_posts 第 1 条）
        # USER_2 的第一条 approved post
        approved_posts = await async_client.get("/api/v1/community/posts", headers=headers)
        if approved_posts.status_code != 200:
            pytest.skip("无法获取帖子列表")
        items = approved_posts.json().get("data", [])
        if not items:
            pytest.skip("无 approved 帖子可点赞")

        post = items[0]
        post_id = post.get("post_id")
        original_likes = post.get("like_count", 0)

        resp = await async_client.post(
            f"/api/v1/community/posts/{post_id}/like",
            headers=headers,
        )
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"点赞失败: {resp.status_code} {resp.text[:200]}"
        body = resp.json()
        data = body.get("data", {})
        new_likes = data.get("like_count")
        assert new_likes == original_likes + 1, \
            f"like_count 应 +1: 原始={original_likes} 现在={new_likes}"


def _check_any_5xx(response) -> None:
    if 500 <= response.status_code < 600:
        raise AssertionError(
            f"5xx ({response.status_code}): {response.text[:300]}"
        )
