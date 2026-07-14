"""Seed checkins table (D6-1): 42 checkins for 21-day checkin E2E testing.

Target: 42 rows (2 users x 21 days x 1 checkin/day)
Note: DB schema unique constraint (user_id, plan_id, day) allows max 1 per day per plan.
      We use 2 users (USER_1 + USER_2) each with their own plan to reach 42 rows.
Uses ON CONFLICT DO UPDATE for idempotent upsert.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import psycopg

USER_1 = uuid.UUID("40e10a9e-329f-4998-a3f0-d36c0ab08abf")
USER_2 = uuid.UUID("f255dff8-9f47-43a6-91c4-932b00c0447f")

VIDEO_IDS = [
    "eb88f20c-ea11-4fdd-ad01-0f1300921a88",
    "fd7042a2-8a59-42b5-ad15-d8a3fcee3335",
    "74198d04-8065-4b71-8525-75a576c35331",
    "f4f6abd4-f870-4911-a652-7333c748acf1",
    "d7fe15fc-350a-4793-9974-9496529d3e01",
    "6387037b-4d99-4f1d-846c-870250c6f29f",
    "854fd3ad-72d7-41a6-893f-7272b81a4fe9",
    "21de5e40-f98b-45b3-a415-73b622632804",
]

NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
SOURCE = "seed"

FEELINGS = [
    "今天感觉精神不错", "睡得还可以", "身体有点疲惫", "心情舒畅", "有点焦虑",
    "状态一般", "精力充沛", "肩颈有点酸", "背部有些僵硬", "整体感觉良好",
    "有点犯困", "神清气爽", "身体轻盈", "感觉放松", "精神奕奕",
    "稍微有点累", "状态不错", "心情愉快", "有点困倦", "身体轻松", "精神状态好",
]


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        # Clean up existing seed checkins first to ensure idempotency
        conn.execute("DELETE FROM checkins WHERE source = 'seed'")
        print("[seed_checkins] Deleted existing seed checkins (idempotency cleanup)")

        # Get plan IDs for both users (must have run seed_plans.py first)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, id FROM plans WHERE source = 'seed' AND status = 'active' AND user_id IN (%s, %s) LIMIT 2",
                (str(USER_1), str(USER_2)),
            )
            rows = cur.fetchall()
            if len(rows) < 2:
                raise RuntimeError(
                    f"Need at least 2 active seed plans (one per user). Found {len(rows)}. "
                    "Run seed_plans.py first."
                )
            plan_map = {str(r[0]): str(r[1]) for r in rows}
            plan_1 = plan_map[str(USER_1)]
            plan_2 = plan_map[str(USER_2)]
            print(f"[seed_checkins] USER_1 plan: {plan_1}")
            print(f"[seed_checkins] USER_2 plan: {plan_2}")

        # 2 users x 21 days = 42 rows
        users_and_plans = [
            (USER_1, plan_1),
            (USER_2, plan_2),
        ]

        inserted = 0
        for user_id, plan_id in users_and_plans:
            for day in range(1, 22):
                video_id = VIDEO_IDS[(day - 1) % len(VIDEO_IDS)]
                created_at = datetime(2026, 7, 7 + day - 1, 9, 0, 0, tzinfo=timezone.utc)

                conn.execute(
                    """
                    INSERT INTO checkins
                        (id, user_id, plan_id, day, video_id, feeling, created_at, deleted_at, source,
                         created_by, created_time, last_updated_time, last_updated_by)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, plan_id, day)
                    DO UPDATE SET
                        video_id = EXCLUDED.video_id,
                        feeling = EXCLUDED.feeling,
                        created_at = EXCLUDED.created_at,
                        source = EXCLUDED.source
                    """,
                    (
                        str(uuid.uuid4()), str(user_id), plan_id, day, video_id,
                        FEELINGS[(day - 1) % len(FEELINGS)], created_at, SOURCE,
                        "seed", created_at, created_at, "seed",
                    ),
                )
                inserted += 1

        print(f"[seed_checkins] Upserted {inserted} checkins (source='{SOURCE}')")

        with conn.cursor() as cur:
            cur.execute("SELECT user_id, COUNT(*) FROM checkins WHERE source = 'seed' GROUP BY user_id ORDER BY user_id")
            print("[seed_checkins] Breakdown by user:")
            for row in cur:
                print(f"  user {row[0]}: {row[1]} rows")
            cur.execute("SELECT COUNT(*) FROM checkins")
            total = cur.fetchone()[0]
            print(f"[seed_checkins] Total checkins in DB: {total} (expected 42)")


if __name__ == "__main__":
    run()
