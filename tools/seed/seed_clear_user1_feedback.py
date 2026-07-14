"""清掉 USER_1 今日 feedback（前面 e2e probe 时手动 POST 了 3 条触发日限）。"""
from __future__ import annotations

import psycopg

USER_1 = "40e10a9e-329f-4998-a3f0-d36c0ab08abf"


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE user_id = %s",
            (USER_1,),
        )
        total = cur.fetchone()[0]
        print(f"[seed_clear_user1_feedback] USER_1 feedback: {total}")

        # USER_1 没 seed → 全清
        cur = conn.execute("DELETE FROM feedback WHERE user_id = %s", (USER_1,))
        print(f"[seed_clear_user1_feedback] deleted {cur.rowcount} rows")


if __name__ == "__main__":
    run()
