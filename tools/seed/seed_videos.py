"""Seed videos table from docs/vedio_contents_collect.{xlsx,json}.

Replaces the 50-row hardcoded dummy seed. Behavior:

1. Wipes ALL rows from ``videos`` (full TRUNCATE-equivalent). The user explicitly
   asked for a full wipe (cascade handled by DB itself).
2. Parses ``vedio_contents_collect.xlsx`` via ``_parse_xlsx.parse_vedio_collect()``
   (falls back to the .json mirror if openpyxl can't open the file).
3. Inserts each parsed row with ``source='seed'`` so downstream queries can still
   tell which rows came from this seed batch.
4. Verifies totals and warns (does NOT fail) when ``MIN_VIDEO_LIBRARY=50`` would
   not be met.

Idempotent: re-running deletes everything again first then re-inserts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from _parse_xlsx import parse_vedio_collect

NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)
SOURCE = "seed"
MIN_VIDEO_LIBRARY = 50

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"
XLSX_PATH = DOCS_DIR / "vedio_contents_collect.xlsx"
JSON_PATH = DOCS_DIR / "vedio_contents_collect.json"

INSERT_SQL = (
    "INSERT INTO videos ("
    "id, title, source, video_id, url, duration_sec, difficulty, tags, thumbnail, "
    "status, created_at, updated_at, deleted_at, "
    "created_by, created_time, last_updated_time, last_updated_by"
    ") VALUES ("
    "%s, %s, %s, %s, %s, %s, %s, %s, %s, "
    "'active', %s, %s, NULL, "
    "%s, %s, %s, %s"
    ")"
)


def run() -> None:
    videos, skipped, skip_samples = parse_vedio_collect(
        xlsx_path=XLSX_PATH,
        json_path=JSON_PATH,
    )

    with psycopg.connect(
        host="localhost",
        port=5432,
        dbname="selfwell",
        user="selfwell",
        password="change_me_in_dev_only",
        autocommit=True,
    ) as conn:
        # Step 1 — wipe ALL videos (user explicit: full wipe, not just 'seed' source).
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM videos")
            deleted = cur.fetchone()[0]
        conn.execute("DELETE FROM videos")
        print(f"[seed_videos] Wiped all videos (TRUNCATE equivalent) — deleted {deleted} rows")

        # Step 2 — insert parsed rows
        inserted = 0
        for v in videos:
            # Stash the parsed-derived fields we need; keep DB column list minimal.
            title = v["title"]
            video_id = v["video_id"]
            url = v["url"]
            duration_sec = v["duration_sec"]
            difficulty = v["difficulty"]
            tags = v["tags"]
            thumbnail = v["thumbnail"]

            conn.execute(
                INSERT_SQL,
                (
                    str(uuid.uuid4()),
                    title,
                    SOURCE,
                    video_id,
                    url,
                    duration_sec,
                    difficulty,
                    psycopg.types.json.Jsonb(tags),
                    thumbnail,
                    NOW,
                    NOW,
                    "seed",
                    NOW,
                    NOW,
                    "seed",
                ),
            )
            inserted += 1

        print(f"[seed_videos] Inserted {inserted} rows from xlsx")

        # Step 3 — verify
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM videos")
            total = cur.fetchone()[0]

        print(f"[seed_videos] Total videos: {total}")
        meets_threshold = total >= MIN_VIDEO_LIBRARY
        print(f"[seed_videos] MIN_VIDEO_LIBRARY={MIN_VIDEO_LIBRARY} met: {meets_threshold}")

    # Diagnostics: skipped cells (parser outcome) only printed outside the SQL txn.
    if skipped:
        print(f"[seed_videos] Skipped cells (no URL extractable): {skipped}")
        for row_idx, reason in skip_samples:
            print(f"[seed_videos]   - row {row_idx}: {reason}")


if __name__ == "__main__":
    run()
