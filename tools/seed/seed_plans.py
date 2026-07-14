"""Seed plans table (D5-1): 10 plans for 21-day plan E2E testing.

Target: 10 rows (2 users x 5 plans each)
Status distribution: active=2, completed=4, abandoned=4
Idempotent: deletes all rows before inserting.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import psycopg

USER_1 = uuid.UUID("40e10a9e-329f-4998-a3f0-d36c0ab08abf")
USER_2 = uuid.UUID("f255dff8-9f47-43a6-91c4-932b00c0447f")

REPORT_IDS = [
    "f7795686-7417-4ae8-ba16-62e15b98d68a",
    "a021d6bc-c3af-46e0-940b-62c237006a83",
    "6c7401f7-1d01-4d80-b1f7-674ecbb829c2",
    "3b1b630c-bb61-4bdc-8790-1bcab2297a52",
    "c9b0fa79-ed2c-4ea2-a3eb-74edc92f570c",
    "91f2c7aa-348e-45ec-bc67-accc020aa038",
    "fa510d9e-a295-4a0a-801b-23ddb9e7427c",
    "9cc8a1ce-3c33-4bbd-9f8b-0be5fb846145",
    "52fcbbd5-168c-452e-9e07-667ebd5a7d24",
    "5ee60413-9914-4aff-bca4-9a91283f342b",
]

NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)
SOURCE = "seed"

TITLES = [
    "肩颈僵硬放松练习",
    "睡前全身拉伸动作",
    "腰背酸痛排查与缓解",
    "头部穴位按摩手法",
    "腿部关节灵活训练",
    "全身经络疏通步骤",
    "女性肩颈舒缓瑜伽",
    "睡前10分钟全身放松",
    "面部刮痧美容手法",
    "臀部经络活化训练",
    "睡前冥想呼吸引导",
    "肩部深层放松按摩",
    "腿部静脉曲张预防",
    "全身有氧拉伸序列",
    "面部轮廓紧致手法",
    "腰部核心力量训练",
    "睡前芳香疗法",
    "头部减压按摩",
    "全身经络拍打",
    "肩颈热敷放松",
    "全身能量恢复",
]


def _make_days(seed: int) -> dict:
    return {
        "items": [
            {
                "day": i + 1,
                "phase": (i // 7) + 1,
                "tasks": [{"title": f"Day{i+1}: {TITLES[(i + seed - 1) % len(TITLES)]}", "video_id": None}],
            }
            for i in range(21)
        ]
    }


PLANS = [
    {"user_id": USER_1, "report_id": REPORT_IDS[0], "days": _make_days(1), "status": "active", "started_at": date(2026, 7, 1), "completed_at": None},
    {"user_id": USER_1, "report_id": REPORT_IDS[1], "days": _make_days(2), "status": "completed", "started_at": date(2026, 6, 10), "completed_at": date(2026, 6, 30)},
    {"user_id": USER_1, "report_id": REPORT_IDS[2], "days": _make_days(3), "status": "completed", "started_at": date(2026, 5, 20), "completed_at": date(2026, 6, 9)},
    {"user_id": USER_1, "report_id": REPORT_IDS[3], "days": _make_days(4), "status": "abandoned", "started_at": date(2026, 5, 1), "completed_at": None},
    {"user_id": USER_1, "report_id": REPORT_IDS[4], "days": _make_days(5), "status": "abandoned", "started_at": date(2026, 4, 15), "completed_at": None},
    {"user_id": USER_2, "report_id": REPORT_IDS[5], "days": _make_days(6), "status": "active", "started_at": date(2026, 7, 7), "completed_at": None},
    {"user_id": USER_2, "report_id": REPORT_IDS[6], "days": _make_days(7), "status": "completed", "started_at": date(2026, 6, 1), "completed_at": date(2026, 6, 21)},
    {"user_id": USER_2, "report_id": REPORT_IDS[7], "days": _make_days(8), "status": "completed", "started_at": date(2026, 5, 10), "completed_at": date(2026, 5, 30)},
    {"user_id": USER_2, "report_id": REPORT_IDS[8], "days": _make_days(9), "status": "abandoned", "started_at": date(2026, 4, 1), "completed_at": None},
    {"user_id": USER_2, "report_id": REPORT_IDS[9], "days": _make_days(10), "status": "abandoned", "started_at": date(2026, 3, 15), "completed_at": None},
]


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        # Cleanup: recall_sessions first (FK refs plans), then plans
        conn.execute("DELETE FROM recall_sessions")
        conn.execute("DELETE FROM plans")
        print("[seed_plans] Deleted all plans + recall_sessions (dev env full refresh)")

        inserted = 0
        for plan in PLANS:
            conn.execute(
                "INSERT INTO plans (id, user_id, report_id, days, status, started_at, completed_at, created_at, deleted_at, source, created_by, created_time, last_updated_time, last_updated_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s)",
                (
                    str(uuid.uuid4()), str(plan["user_id"]), plan["report_id"],
                    psycopg.types.json.Jsonb(plan["days"]), plan["status"],
                    plan["started_at"], plan["completed_at"], NOW,
                    SOURCE, "seed", NOW, NOW, "seed",
                ),
            )
            inserted += 1

        print(f"[seed_plans] Inserted {inserted} plans (source='{SOURCE}')")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM plans WHERE source = %s", ("seed",))
            print(f"[seed_plans] Verified: {cur.fetchone()[0]} seed plans in DB (expected 10)")


if __name__ == "__main__":
    run()
