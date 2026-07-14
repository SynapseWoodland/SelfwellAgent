"""Seed feedback table (D8-1): 30 feedback rows for M8 recall data source.

Target: 30 rows (21 days x ~1.5 feedback/day ≈ 30)
Idempotent: deletes all rows before inserting.
Valid feedback_type: mood_text, mood_photo, period_photo, plan_compare_photo
Valid body_part: face, head, shoulder_neck, waist, leg, overall_look
mood_photo requires non-null photo_url.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import psycopg

USER_2 = uuid.UUID("f255dff8-9f47-43a6-91c4-932b00c0447f")
SOURCE = "seed"
BASE_DATE = date(2026, 7, 13)

# Valid body_part values per schema
BODY_PARTS = ["face", "head", "shoulder_neck", "waist", "leg", "overall_look"]

FEEDBACKS = [
    # mood_text: requires text_content NOT NULL, photo_url NULL
    {"day_offset": -20, "feedback_type": "mood_text", "text": "今天心情很好，做了肩颈练习感觉很舒服", "photo_url": None, "body_part": None},
    {"day_offset": -19, "feedback_type": "mood_text", "text": "今天状态一般", "photo_url": None, "body_part": None},
    {"day_offset": -18, "feedback_type": "mood_text", "text": "练习效果不错，身体感觉轻松多了", "photo_url": None, "body_part": None},
    {"day_offset": -17, "feedback_type": "mood_text", "text": "睡眠质量提升了", "photo_url": None, "body_part": None},
    {"day_offset": -16, "feedback_type": "mood_text", "text": "最近压力有点大", "photo_url": None, "body_part": None},
    {"day_offset": -15, "feedback_type": "mood_text", "text": "坚持了一周，感觉精神好了很多", "photo_url": None, "body_part": None},
    {"day_offset": -14, "feedback_type": "mood_text", "text": "完成了14天打卡，很开心", "photo_url": None, "body_part": None},
    {"day_offset": -13, "feedback_type": "mood_text", "text": "今天练习完成", "photo_url": None, "body_part": None},
    {"day_offset": -12, "feedback_type": "mood_text", "text": "身体状态越来越好", "photo_url": None, "body_part": None},
    {"day_offset": -11, "feedback_type": "mood_text", "text": "有点焦虑", "photo_url": None, "body_part": None},
    {"day_offset": -10, "feedback_type": "mood_text", "text": "今天心情愉快", "photo_url": None, "body_part": None},
    {"day_offset": -9, "feedback_type": "mood_text", "text": "感觉身体轻盈了很多", "photo_url": None, "body_part": None},
    {"day_offset": -8, "feedback_type": "mood_text", "text": "一般般", "photo_url": None, "body_part": None},
    {"day_offset": -7, "feedback_type": "mood_text", "text": "完成了7天打卡，进步明显", "photo_url": None, "body_part": None},
    {"day_offset": -6, "feedback_type": "mood_text", "text": "精神状态好", "photo_url": None, "body_part": None},
    {"day_offset": -5, "feedback_type": "mood_text", "text": "今天心情低落", "photo_url": None, "body_part": None},
    {"day_offset": -4, "feedback_type": "mood_text", "text": "打卡完成", "photo_url": None, "body_part": None},
    {"day_offset": -3, "feedback_type": "mood_text", "text": "身体感觉不错", "photo_url": None, "body_part": None},
    {"day_offset": -2, "feedback_type": "mood_text", "text": "日常打卡", "photo_url": None, "body_part": None},
    {"day_offset": -1, "feedback_type": "mood_text", "text": "期待蜕变完成", "photo_url": None, "body_part": None},
    {"day_offset": 0, "feedback_type": "mood_text", "text": "今天是第21天！坚持完成了", "photo_url": None, "body_part": None},
    # mood_photo: requires photo_url NOT NULL, text_content NULL
    {"day_offset": -20, "feedback_type": "mood_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=10", "body_part": None},
    {"day_offset": -15, "feedback_type": "mood_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=11", "body_part": None},
    {"day_offset": -12, "feedback_type": "mood_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=12", "body_part": None},
    {"day_offset": -7, "feedback_type": "mood_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=13", "body_part": None},
    {"day_offset": -6, "feedback_type": "mood_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=14", "body_part": None},
    {"day_offset": 0, "feedback_type": "mood_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=15", "body_part": None},
    # period_photo: requires photo_url NOT NULL, body_part required
    {"day_offset": -18, "feedback_type": "period_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=20", "body_part": "shoulder_neck"},
    {"day_offset": -16, "feedback_type": "period_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=21", "body_part": "waist"},
    {"day_offset": -14, "feedback_type": "period_photo", "text": None, "photo_url": "https://picsum.photos/400/300?random=22", "body_part": "leg"},
]


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        conn.execute("DELETE FROM feedback")
        print("[seed_feedback] Deleted all feedback (dev env full refresh)")

        inserted = 0
        for fb in FEEDBACKS:
            fb_date = BASE_DATE + timedelta(days=fb["day_offset"])
            created_at = datetime(fb_date.year, fb_date.month, fb_date.day, 10, 0, 0, tzinfo=timezone.utc)

            conn.execute(
                "INSERT INTO feedback (id, user_id, feedback_type, text_content, photo_url, body_part, ai_ack_id, deleted_at, created_at, source, created_by, created_time, last_updated_time, last_updated_by) VALUES (%s, %s, %s, %s, %s, %s, NULL, NULL, %s, %s, %s, %s, %s, %s)",
                (
                    str(uuid.uuid4()), str(USER_2), fb["feedback_type"], fb["text"], fb["photo_url"],
                    fb["body_part"], created_at, SOURCE, "seed", created_at, created_at, "seed",
                ),
            )
            inserted += 1

        print(f"[seed_feedback] Inserted {inserted} feedback rows (source='{SOURCE}')")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM feedback")
            total = cur.fetchone()[0]
            print(f"[seed_feedback] Verified: {total} feedback in DB (expected 30)")


if __name__ == "__main__":
    run()
