"""清掉 USER_1 今日 posts（前面 e2e 跑测试时触发 24h ≤ 3 条限）。"""
from __future__ import annotations

import psycopg

USER_1 = "40e10a9e-329f-4998-a3f0-d36c0ab08abf"


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        # 软删
        cur = conn.execute(
            "UPDATE posts SET deleted_at = NOW() "
            "WHERE user_id = %s "
            "AND created_at >= NOW() - INTERVAL '24 hours' "
            "AND deleted_at IS NULL "
            "RETURNING id",
            (USER_1,),
        )
        deleted = cur.fetchall()
        print(f"[seed_clear_user1_posts] soft-deleted {len(deleted)} posts")


if __name__ == "__main__":
    run()
