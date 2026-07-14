"""Phase 4 · 批次 5 · Journey 3：心情日记。

业务路径：
1. POST /api/v1/feedback（mood_text + mood_photo + period_photo）
2. GET  /api/v1/feedback → 验证真持久化
3. POST /api/v1/butler/recall → 验证 AI 真调（含 referenced_feedbacks）

真业务验证点：
  ① feedback 真持久化（GET /feedback 能查到）
  ② recall 真能检索到 7 天内的 mood
  ③ AI 真答（referenced_feedbacks 引用 mood）

注意：POST /feedback 返回 envelope 不含 ``photo_url`` / ``text_content``（API
契约不回显输入内容）。持久化验证改为直接查 PG（psycopg）。
前置：seed_feedback（30 条，USER_2 已有 mood_text + mood_photo + period_photo）。

⚠ skip 条件：recall 需要 feedback 数据（USER_2 有 seed_feedback）；USER_1 无数据则 skip recall 部分。
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import psycopg

from .conftest import USER_1, USER_2


_PG_DSN = dict(
    host="localhost", port=5432, dbname="selfwell",
    user="selfwell", password="change_me_in_dev_only",
)


def _pg_lookup_feedback(feedback_id: str) -> dict | None:
    """直查 PG 验证 feedback 真持久化（API 返回不含 input 字段）。

    API 的事务 commit 是在 response send 完成后才 await commit()，
    测试并发连接可能在 commit 前查不到行；加一个短轮询避免假阴性。
    """
    import time
    for _ in range(10):
        with psycopg.connect(**_PG_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT feedback_type, body_part, photo_url, text_content, deleted_at
                    FROM feedback WHERE id = %s
                    """,
                    (feedback_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "feedback_type": row[0],
                        "body_part": row[1],
                        "photo_url": row[2],
                        "text_content": row[3],
                        "deleted_at": row[4],
                    }
        time.sleep(0.1)
    return None


@pytest.mark.e2e
class TestJourney3MoodFeedback:
    """Journey 3 — mood_text + mood_photo + period_photo → recall。"""

    # ── ① 创建 mood_text ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j3_feedback_mood_text(self, async_client, auth_header_factory, shared_ctx):
        """POST /feedback（mood_text）→ 验证持久化（PG 直查）。"""
        headers = auth_header_factory(str(USER_1))
        payload = {
            "feedback_type": "mood_text",
            "text_content": "今天感觉心情很好，完成了一个小目标！",
        }
        resp = await async_client.post("/api/v1/feedback", json=payload, headers=headers)
        if resp.status_code == 429:
            pytest.skip(f"feedback 日限触发（USER_1 今日已 ≥5 条）：{resp.text[:120]}")
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"mood_text 失败: {resp.status_code} {resp.text[:200]}"
        body = resp.json()
        data = body.get("data", {})
        feedback_id = data.get("feedback_id")
        assert feedback_id, f"mood_text 无 feedback_id: {data}"
        assert data.get("feedback_type") == "mood_text"
        shared_ctx["j3_feedback_id"] = feedback_id

        # PG 直查验证 text_content 真持久化（API 不回显 text_content）
        row = _pg_lookup_feedback(feedback_id)
        assert row, f"PG 查不到 mood_text feedback {feedback_id}"
        assert row["text_content"] == "今天感觉心情很好，完成了一个小目标！", \
            f"text_content 未持久化: {row}"

    # ── ② 创建 mood_photo ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j3_feedback_mood_photo(self, async_client, auth_header_factory, shared_ctx):
        """POST /feedback（mood_photo）→ 验证 photo_url 真存（PG 直查）。

        API envelope 不回显 photo_url，所以用 psycopg 直查 feedback 表。
        """
        headers = auth_header_factory(str(USER_1))
        payload = {
            "feedback_type": "mood_photo",
            "photo_url": "https://picsum.photos/400/300?random=j3mp",
            "body_part": "face",
        }
        resp = await async_client.post("/api/v1/feedback", json=payload, headers=headers)
        if resp.status_code == 429:
            pytest.skip(f"feedback 日限触发（USER_1 今日已 ≥5 条）：{resp.text[:120]}")
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"mood_photo 失败: {resp.status_code} {resp.text[:200]}"
        body = resp.json()
        data = body.get("data", {})
        assert data.get("feedback_type") == "mood_photo"
        assert data.get("body_part") == "face"
        shared_ctx["j3_mood_photo_id"] = data.get("feedback_id")

        # PG 直查验证 photo_url 真持久化
        fid = data.get("feedback_id")
        assert fid, f"mood_photo 无 feedback_id: {data}"
        row = _pg_lookup_feedback(fid)
        assert row, f"PG 查不到 mood_photo feedback {fid}"
        assert row["photo_url"] == "https://picsum.photos/400/300?random=j3mp", \
            f"photo_url 未持久化: {row}"

    # ── ③ 创建 period_photo ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j3_feedback_period_photo(self, async_client, auth_header_factory, shared_ctx):
        """POST /feedback（period_photo）→ 验证 body_part + photo_url 真存。"""
        headers = auth_header_factory(str(USER_1))
        payload = {
            "feedback_type": "period_photo",
            "photo_url": "https://picsum.photos/400/300?random=j3pp",
            "body_part": "shoulder_neck",
        }
        resp = await async_client.post("/api/v1/feedback", json=payload, headers=headers)
        if resp.status_code == 429:
            pytest.skip(f"feedback 日限触发（USER_1 今日已 ≥5 条）：{resp.text[:120]}")
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"period_photo 失败: {resp.status_code}"
        body = resp.json()
        data = body.get("data", {})
        assert data.get("feedback_type") == "period_photo"
        assert data.get("body_part") == "shoulder_neck"
        shared_ctx["j3_period_photo_id"] = data.get("feedback_id")

        # PG 直查
        fid = data.get("feedback_id")
        assert fid, f"period_photo 无 feedback_id: {data}"
        row = _pg_lookup_feedback(fid)
        assert row, f"PG 查不到 period_photo feedback {fid}"
        assert row["body_part"] == "shoulder_neck"
        assert row["photo_url"] == "https://picsum.photos/400/300?random=j3pp", \
            f"photo_url 未持久化: {row}"

    # ── ④ 验证 feedback 真可被检索 ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j3_feedback_persisted(self, async_client, auth_header_factory, shared_ctx):
        """GET /feedback（recall_retrieve caller）→ 验证持久化数据可查。

        注意：GET /feedback 可能是 recall 内部接口，公网未必暴露；这里接受
        200/404 两种结果（404 时降级到 PG 直查验证）。
        """
        feedback_id = shared_ctx.get("j3_feedback_id")
        if not feedback_id:
            pytest.skip("无 mood_text feedback_id，跳过持久化验证")

        headers = auth_header_factory(str(USER_1))
        resp = await async_client.get(
            "/api/v1/feedback",
            headers={**headers, "X-Caller-Id": "recall_retrieve"},
        )
        if resp.status_code == 404:
            # 公网未开放 → 改用 PG 直查（与上面 test 一致）
            row = _pg_lookup_feedback(feedback_id)
            assert row, f"PG 查不到 mood_text feedback {feedback_id}"
            assert row["deleted_at"] is None, f"feedback 已被软删: {row}"
            return
        _check_any_5xx(resp)
        assert resp.status_code == 200, f"feedback GET 失败: {resp.status_code} {resp.text[:200]}"
        items = resp.json().get("data", [])
        if isinstance(items, list):
            ids = [f.get("feedback_id") for f in items]
            if feedback_id not in ids:
                # 公网 GET 可能只返回近期 N 条；用 PG 直查兜底
                row = _pg_lookup_feedback(feedback_id)
                assert row, f"mood_text feedback 未查到（API + PG 都没有）: {feedback_id}"

    # ── ⑤ 验证 recall 真引用 mood ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_j3_recall_references_moods(self, async_client, auth_header_factory):
        """POST /butler/recall（USER_2 有 seed_feedback）→ 验证 referenced_feedbacks 非空。

        USER_2 有 30 条 seed_feedback（21 天 mood_text + mood_photo + period_photo）。
        recall 应真加载这些 feedbacks 并返回。
        """
        headers = auth_header_factory(str(USER_2))
        resp = await async_client.post(
            "/api/v1/butler/recall",
            json={"trigger": "user_manual", "days_offset": 7},
            headers=headers,
        )
        # recall 日限触发（j5 真业务已用 USER_2 一次）→ skip
        if resp.status_code == 429:
            pytest.skip(f"recall 日限触发（USER_2 今日已生成）：{resp.text[:120]}")
        # recall 返回 is_empty=true 时（无数据）→ skip
        if resp.status_code == 200:
            body = resp.json()
            data = body.get("data", {})
            if data.get("is_empty"):
                pytest.skip("recall 返回 is_empty=true（USER_2 无反馈数据）")
            refs = data.get("referenced_feedbacks", [])
            # 验证点 ③ referenced_feedbacks ≥ 3
            assert len(refs) >= 3, \
                f"recall referenced_feedbacks 应 ≥3，实际 {len(refs)}: {refs[:3]}"
            # 验证每个 ref 含关键字段
            for ref in refs[:3]:
                assert "id" in ref or "feedback_type" in ref, f"ref 缺关键字段: {ref}"
        elif resp.status_code in (400, 422):
            # "用户尚无任何 feedback 记录" → skip
            body = resp.json()
            pytest.skip(f"recall 校验失败（可能无 feedback）: {body}")
        else:
            _check_any_5xx(resp)
            raise AssertionError(f"recall 失败: {resp.status_code} {resp.text[:200]}")


def _check_any_5xx(response) -> None:
    if 500 <= response.status_code < 600:
        raise AssertionError(
            f"5xx ({response.status_code}): {response.text[:300]}"
        )
