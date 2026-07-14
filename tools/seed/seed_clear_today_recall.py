"""清掉今日的 recall_sessions，让 USER_2 的 recall POST 不被日限卡住。

recall_service.generate_recall 限制每用户 24h ≤ 1 次。之前 e2e probe 触发了
USER_2 的 recall POST，今天已生成 1 条。journey 5 的 recall_user_query 需要
再触发一次 → 必须先清掉。

不动 seed_recall_sessions.py / run_all.py。
"""
from __future__ import annotations

import psycopg

USER_2 = "f255dff8-9f47-43a6-91c4-932b00c0447f"


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        cur = conn.execute(
            """
            SELECT id, created_at, trigger FROM recall_sessions
            WHERE user_id = %s
              AND created_at >= NOW() - INTERVAL '24 hours'
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            """,
            (USER_2,),
        )
        rows = list(cur)
        print(f"[seed_clear_today_recall] USER_2 近 24h recall: {len(rows)}")
        for r in rows:
            print(" ", r)

        if not rows:
            print("[seed_clear_today_recall] 无需清理")
            return

        # 软删（deleted_at）而非硬删，避免破坏 ai_messages 关联
        ids = [r[0] for r in rows]
        conn.execute(
            """
            UPDATE recall_sessions
            SET deleted_at = NOW()
            WHERE id = ANY(%s::uuid[])
            """,
            (ids,),
        )
        print(f"[seed_clear_today_recall] soft-deleted {len(ids)} recall_sessions")


if __name__ == "__main__":
    run()
