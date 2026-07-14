"""扩展 USER_2 feedback 日期跨度，覆盖近 10 个 ISO 周。

策略：每条 feedback 的 created_at 错开（按索引）天，整体往前推 49 天 →
30 条 feedback 横跨 30 天 ≈ 5 周。再叠加「每 3 条之间跳一周」的错峰可以
拉到 7-8 周。

不动 seed_feedback.py / run_all.py。
"""
from __future__ import annotations

from datetime import timedelta

import psycopg

USER_2 = "f255dff8-9f47-43a6-91c4-932b00c0447f"


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        cur = conn.execute(
            """
            SELECT id, created_at FROM feedback
            WHERE user_id = %s
            ORDER BY created_at, id
            """,
            (USER_2,),
        )
        rows = cur.fetchall()
        print(f"[seed_extend_feedback_dates] USER_2 feedback 总数: {len(rows)}")

        if not rows:
            print("[seed_extend_feedback_dates] 没有 feedback 可更新")
            return

        # 把最早一条的日期定为「今天的 9 周前」
        base_old = rows[0][1]
        target_anchor = rows[-1][1] + timedelta(days=-63)  # 整体往前 63 天
        delta = target_anchor - base_old  # 偏移量

        # 每条 + (delta + idx) 天，让 30 条横跨至少 30 天 ≈ 5 周
        updated = 0
        for i, (fid, old_ts) in enumerate(rows):
            new_ts = old_ts + delta + timedelta(days=i * 1.5)
            # 同时改 created_at + created_time（album_service 用 created_time）
            conn.execute(
                "UPDATE feedback SET created_at = %s, created_time = %s WHERE id = %s",
                (new_ts, new_ts, fid),
            )
            updated += 1
        print(
            f"[seed_extend_feedback_dates] updated {updated} rows, "
            f"delta={delta.days}d, span=1.5d/row"
        )

        cur = conn.execute(
            """
            SELECT EXTRACT(ISOYEAR FROM created_at)::int AS y,
                   EXTRACT(WEEK FROM created_at)::int AS w,
                   COUNT(*)
            FROM feedback
            WHERE user_id = %s
            GROUP BY y, w
            ORDER BY y, w
            """,
            (USER_2,),
        )
        weeks = list(cur)
        print(f"[seed_extend_feedback_dates] 覆盖 ISO 周: {len(weeks)}")
        for y, w, c in weeks:
            print(f"  {y}-W{w:02d}: {c} feedback")

        # 验证近 10 周覆盖
        from datetime import date, timedelta as td
        today = date(2026, 7, 14)
        recent_weeks = set()
        for i in range(10):
            d = today - td(days=7 * i)
            iso = d.isocalendar()
            recent_weeks.add((iso[0], iso[1]))
        covered = sum(1 for y, w, _ in weeks if (y, w) in recent_weeks)
        print(
            f"[seed_extend_feedback_dates] 近 10 周有数据的周数: {covered}"
        )


if __name__ == "__main__":
    run()
