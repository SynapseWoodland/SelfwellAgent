"""把 USER_2 feedback 的 created_time + created_at 复位到与 seed_feedback 一致。

seed_feedback 原基准日是 2026-07-13。feedback 创建逻辑：
  created_at = BASE_DATE + day_offset  (10:00 UTC)
  created_time = created_at
但前面 seed_extend_feedback_dates 推了 -43 天后，现在又跑一次就会推到很早。
此脚本重新基于 2026-07-13 基准，把所有行 reset 后再交给 seed_extend 重新排。
"""
from __future__ import annotations

import psycopg
from datetime import datetime, timedelta, timezone

USER_2 = "f255dff8-9f47-43a6-91c4-932b00c0447f"
BASE_DATE = datetime(2026, 7, 13, 10, 0, 0, tzinfo=timezone.utc)


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        cur = conn.execute(
            "SELECT id FROM feedback WHERE user_id = %s ORDER BY created_time",
            (USER_2,),
        )
        ids = [r[0] for r in cur]
        print(f"[reset_feedback_dates] USER_2 feedback: {len(ids)}")

        # 按 id 顺序排列到 day_offset = 0..N-1 前的某个范围
        # 原 seed_feedback 实际有 30 条，day_offset 范围 -20..0
        for i, fid in enumerate(ids):
            day_offset = -20 + i * 0.7  # 30 条跨 ~21 天
            new_ts = BASE_DATE + timedelta(days=day_offset)
            conn.execute(
                "UPDATE feedback SET created_at = %s, created_time = %s WHERE id = %s",
                (new_ts, new_ts, fid),
            )
        print(f"[reset_feedback_dates] reset {len(ids)} rows")


if __name__ == "__main__":
    run()
