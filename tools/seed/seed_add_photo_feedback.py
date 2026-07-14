"""扩展 USER_2 feedback 中含 photo_url 的条目数，让近 10 周内 ≥7 周有照片。

策略：把一部分 mood_text 行的 photo_url 从 NULL 改为 picsum URL → 实际不算
（schema 要求 mood_text 的 photo_url 必须 NULL）。改用：把一部分 mood_text
转换成 period_photo / mood_photo 并设置 photo_url + body_part。

不动 seed_feedback.py / run_all.py。
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
            SELECT id, created_at FROM feedback
            WHERE user_id = %s AND feedback_type = 'mood_text'
            ORDER BY created_at
            """,
            (USER_2,),
        )
        rows = list(cur)
        print(f"[seed_add_photo_feedback] mood_text 总数: {len(rows)}")

        if len(rows) < 5:
            print("[seed_add_photo_feedback] 没有足够 mood_text 可改")
            return

        # 均匀选 8 条转 mood_photo，覆盖更多 ISO 周
        step = max(1, len(rows) // 8)
        ids_to_convert = [rows[i][0] for i in range(0, len(rows), step)][:8]

        for fid in ids_to_convert:
            new_photo = f"https://picsum.photos/400/300?random=extend-{str(fid)[:8]}"
            conn.execute(
                """
                UPDATE feedback
                SET feedback_type = 'mood_photo',
                    photo_url = %s,
                    body_part = COALESCE(body_part, 'face'),
                    text_content = NULL
                WHERE id = %s
                """,
                (new_photo, fid),
            )
        print(f"[seed_add_photo_feedback] convert {len(ids_to_convert)} rows to mood_photo")

        # 再选 5 条转 period_photo 进一步覆盖
        cur = conn.execute(
            """
            SELECT id FROM feedback
            WHERE user_id = %s AND feedback_type = 'mood_text'
            ORDER BY created_at LIMIT 5 OFFSET 4
            """,
            (USER_2,),
        )
        period_ids = [r[0] for r in cur]
        for fid in period_ids:
            new_photo = f"https://picsum.photos/400/300?random=period-{str(fid)[:8]}"
            conn.execute(
                """
                UPDATE feedback
                SET feedback_type = 'period_photo',
                    photo_url = %s,
                    body_part = 'shoulder_neck',
                    text_content = NULL
                WHERE id = %s
                """,
                (new_photo, fid),
            )
        print(f"[seed_add_photo_feedback] convert {len(period_ids)} rows to period_photo")

        cur = conn.execute(
            """
            SELECT feedback_type, COUNT(*)
            FROM feedback
            WHERE user_id = %s
            GROUP BY feedback_type ORDER BY feedback_type
            """,
            (USER_2,),
        )
        for row in cur:
            print(" ", row)

        # 验证：近 10 周有 photo_url 的 ISO 周数
        from datetime import date, timedelta as td
        cur = conn.execute(
            """
            SELECT EXTRACT(ISOYEAR FROM created_at)::int AS y,
                   EXTRACT(WEEK FROM created_at)::int AS w,
                   COUNT(*)
            FROM feedback
            WHERE user_id = %s
              AND photo_url IS NOT NULL
              AND created_at >= %s
            GROUP BY y, w ORDER BY y, w
            """,
            (USER_2, date(2026, 7, 14) - td(days=70)),
        )
        weeks_with_photo = list(cur)
        print(
            f"[seed_add_photo_feedback] 近 10 周含 photo 的 ISO 周数: "
            f"{len(weeks_with_photo)}"
        )
        for y, w, c in weeks_with_photo:
            print(f"  {y}-W{w:02d}: {c}")


if __name__ == "__main__":
    run()
