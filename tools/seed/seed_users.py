"""Seed users table (Phase 4 batch 5 prerequisite): seed USER_1 + USER_2 referenced by other seeds.

Inserts two users with deterministic IDs used by seed_plans / seed_checkins / seed_feedback /
seed_recall_sessions / seed_posts to keep FK referential integrity.

Idempotent: upserts by id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import psycopg

NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
SOURCE = "seed"

USER_1 = uuid.UUID("40e10a9e-329f-4998-a3f0-d36c0ab08abf")
USER_2 = uuid.UUID("f255dff8-9f47-43a6-91c4-932b00c0447f")

USERS = [
    {
        "id": USER_1,
        "unionid": "seed-unionid-user1",
        "openid_mp": "seed-openid-mp-user1",
        "phone": "13800000001",
        "platform": "wx_mp",
        "device_id": "seed-device-user1",
        "nickname": "测试用户小满",
        "avatar": "https://dummyimage.com/200x200/A8C5B5/ffffff?text=小满",
        "age_range": "23-28",
        "sitting_hours": "4-8h",
        "focus_parts": {"items": ["shoulder_neck", "waist"]},
        "intensity": "适中",
        "preferred_time": "不固定",
        "status": "active",
    },
    {
        "id": USER_2,
        "unionid": "seed-unionid-user2",
        "openid_mp": "seed-openid-mp-user2",
        "phone": "13800000002",
        "platform": "wx_mp",
        "device_id": "seed-device-user2",
        "nickname": "测试用户阿木",
        "avatar": "https://dummyimage.com/200x200/D4C5E2/ffffff?text=阿木",
        "age_range": "29-35",
        "sitting_hours": "8-12h",
        "focus_parts": {"items": ["head", "face", "overall_look"]},
        "intensity": "轻柔",
        "preferred_time": "晚",
        "status": "active",
    },
]


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        for u in USERS:
            conn.execute(
                """
                INSERT INTO users (
                    id, unionid, openid_mp, phone, platform, device_id,
                    nickname, avatar, age_range, sitting_hours, focus_parts,
                    intensity, preferred_time, status,
                    created_at, last_active_at, version,
                    created_by, created_time, last_updated_time, last_updated_by
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, 0,
                    %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    unionid = EXCLUDED.unionid,
                    nickname = EXCLUDED.nickname,
                    age_range = EXCLUDED.age_range,
                    sitting_hours = EXCLUDED.sitting_hours,
                    focus_parts = EXCLUDED.focus_parts,
                    intensity = EXCLUDED.intensity,
                    preferred_time = EXCLUDED.preferred_time,
                    last_active_at = EXCLUDED.last_active_at
                """,
                (
                    str(u["id"]), u["unionid"], u["openid_mp"], u["phone"],
                    u["platform"], u["device_id"],
                    u["nickname"], u["avatar"], u["age_range"], u["sitting_hours"],
                    psycopg.types.json.Jsonb(u["focus_parts"]),
                    u["intensity"], u["preferred_time"], u["status"],
                    NOW, NOW, SOURCE, NOW, NOW, SOURCE,
                ),
            )
        print(f"[seed_users] Upserted {len(USERS)} users (USER_1 + USER_2)")
        with conn.cursor() as cur:
            cur.execute("SELECT id, nickname, status FROM users WHERE id IN (%s, %s)", (str(USER_1), str(USER_2)))
            for row in cur:
                print(f"  {row[0]} | {row[1]} | {row[2]}")


if __name__ == "__main__":
    run()