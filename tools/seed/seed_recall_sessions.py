"""Seed recall_sessions table (D7-1): 5 sessions for M8 active recall E2E testing.

Target: 5 rows covering 4 trigger types + 1 empty state
Valid trigger: user_query, auto_day7, auto_day14, auto_day21
ai_encourage max 80 chars
Idempotent: deletes all rows before inserting.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import psycopg

USER_2 = uuid.UUID("f255dff8-9f47-43a6-91c4-932b00c0447f")
SOURCE = "seed"
BODY_PARTS = ["face", "head", "shoulder_neck", "waist", "leg", "overall_look"]

SESSIONS = [
    # 1. user_query with 3 referenced feedbacks
    {
        "trigger": "user_query",
        "ai_summary": "在过去的三天里，你的心情整体积极向上。Day -20 你感觉肩颈舒服，Day -18 身体感觉轻松多了。",
        "ai_encourage": "你已经在练习中找到了舒适感，这很棒！继续保持。",
        "referenced_feedbacks": [
            {"id": "seed-fb-1", "body_part": "shoulder_neck", "snippet": "今天心情很好，做了肩颈练习感觉很舒服", "created_at": "2026-06-23T10:00:00Z"},
            {"id": "seed-fb-2", "body_part": "overall_look", "snippet": "练习效果不错，身体感觉轻松多了", "created_at": "2026-06-25T10:00:00Z"},
            {"id": "seed-fb-3", "body_part": "shoulder_neck", "snippet": "肩颈有点酸痛", "created_at": "2026-06-25T10:00:00Z"},
        ],
        "referenced_photos": [],
        "llm_cost": "0.0025",
        "safety_passed": True,
        "created_at": datetime(2026, 7, 13, 10, 0, 0, tzinfo=timezone.utc),
    },
    # 2. auto_day7 with 7 referenced feedbacks
    {
        "trigger": "auto_day7",
        "ai_summary": "7天的坚持让你有了明显的进步。从最初的肩颈酸痛到现在的轻松舒适，你的心态也更加积极。",
        "ai_encourage": "第一周的完成值得庆祝！你已经迈出了重要的一步。",
        "referenced_feedbacks": [
            {"id": "seed-fb-4", "body_part": "shoulder_neck", "snippet": "今天状态一般", "created_at": "2026-06-24T10:00:00Z"},
            {"id": "seed-fb-5", "body_part": "face", "snippet": "睡眠质量提升了", "created_at": "2026-06-24T10:00:00Z"},
            {"id": "seed-fb-6", "body_part": "waist", "snippet": "背部有点僵硬", "created_at": "2026-06-25T10:00:00Z"},
            {"id": "seed-fb-7", "body_part": "shoulder_neck", "snippet": "有点焦虑", "created_at": "2026-06-25T10:00:00Z"},
            {"id": "seed-fb-8", "body_part": "shoulder_neck", "snippet": "坚持了一周，感觉精神好了很多", "created_at": "2026-06-26T10:00:00Z"},
            {"id": "seed-fb-9", "body_part": "leg", "snippet": "腿部有点疲劳", "created_at": "2026-06-26T10:00:00Z"},
            {"id": "seed-fb-10", "body_part": "shoulder_neck", "snippet": "今天练习完成", "created_at": "2026-06-27T10:00:00Z"},
        ],
        "referenced_photos": [],
        "llm_cost": "0.0050",
        "safety_passed": True,
        "created_at": datetime(2026, 7, 14, 9, 0, 0, tzinfo=timezone.utc),
    },
    # 3. auto_day14 with 14 referenced feedbacks
    {
        "trigger": "auto_day14",
        "ai_summary": "两周的坚持让你在身体和心灵上都收获满满。从最初的焦虑慢慢转向平静和积极。",
        "ai_encourage": "两周的坚持不易，你做到了！愿你继续保持这份热情。",
        "referenced_feedbacks": [
            {"id": f"seed-fb-{i}", "body_part": "shoulder_neck", "snippet": f"feedback day {i}", "created_at": f"2026-06-{20+i:02d}T10:00:00Z"}
            for i in range(2, 16)
        ],
        "referenced_photos": [],
        "llm_cost": "0.0100",
        "safety_passed": True,
        "created_at": datetime(2026, 7, 21, 9, 0, 0, tzinfo=timezone.utc),
    },
    # 4. auto_day21 with 21 referenced feedbacks
    {
        "trigger": "auto_day21",
        "ai_summary": "21天的坚持是一段美妙的旅程。从第一天的紧张焦虑，到现在的平静自信。",
        "ai_encourage": "恭喜你完成了21天的蜕变计划！这段坚持本身就是最大的胜利。",
        "referenced_feedbacks": [
            {"id": f"seed-fb-day{i}", "body_part": BODY_PARTS[i % len(BODY_PARTS)], "snippet": f"Day {i} feedback entry", "created_at": f"2026-07-{min(i,9):02d}T10:00:00Z"}
            for i in range(-20, 1)
        ],
        "referenced_photos": [],
        "llm_cost": "0.0150",
        "safety_passed": True,
        "created_at": datetime(2026, 7, 28, 9, 0, 0, tzinfo=timezone.utc),
    },
    # 5. user_query empty state (0 feedbacks)
    {
        "trigger": "user_query",
        "ai_summary": None,
        "ai_encourage": "还没有记录心情日记哦~开始记录你的第一条心情吧！",
        "referenced_feedbacks": [],
        "referenced_photos": [],
        "llm_cost": "0.0001",
        "safety_passed": True,
        "created_at": datetime(2026, 7, 10, 14, 0, 0, tzinfo=timezone.utc),
    },
]


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        conn.execute("DELETE FROM recall_sessions")
        print("[seed_recall_sessions] Deleted all recall_sessions (dev env full refresh)")

        inserted = 0
        for sess in SESSIONS:
            conn.execute(
                "INSERT INTO recall_sessions (id, user_id, plan_id, trigger, ai_summary, ai_encourage, referenced_feedbacks, referenced_photos, llm_cost, safety_passed, ai_session_id, created_at, deleted_at, source, created_by, created_time, last_updated_time, last_updated_by) VALUES (%s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, NULL, %s, NULL, %s, %s, %s, %s, %s)",
                (
                    str(uuid.uuid4()), str(USER_2), sess["trigger"], sess["ai_summary"], sess["ai_encourage"],
                    psycopg.types.json.Jsonb(sess["referenced_feedbacks"]),
                    psycopg.types.json.Jsonb(sess["referenced_photos"]),
                    sess["llm_cost"], sess["safety_passed"],
                    sess["created_at"], SOURCE, "seed", sess["created_at"], sess["created_at"], "seed",
                ),
            )
            inserted += 1

        print(f"[seed_recall_sessions] Inserted {inserted} sessions (source='{SOURCE}')")

        with conn.cursor() as cur:
            cur.execute("SELECT trigger, COUNT(*) FROM recall_sessions GROUP BY trigger ORDER BY trigger")
            print("[seed_recall_sessions] Breakdown by trigger:")
            for row in cur:
                print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    run()
