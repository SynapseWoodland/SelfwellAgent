"""清掉 USER_1 今日 feedback（前面 e2e probe 时 POST 了 6 条触发日限）。"""
from __future__ import annotations

import psycopg

USER_1 = "40e10a9e-329f-4998-a3f0-d36c0ab08abf"


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        cur = conn.execute(
            "UPDATE feedback SET deleted_at = NOW() "
            "WHERE user_id = %s "
            "AND created_time >= NOW() - INTERVAL '24 hours' "
            "AND deleted_at IS NULL "
            "RETURNING id",
            (USER_1,),
        )
        deleted = cur.fetchall()
        print(f"[seed_clear_user1_feedback_today] soft-deleted {len(deleted)}")


if __name__ == "__main__":
    run()
