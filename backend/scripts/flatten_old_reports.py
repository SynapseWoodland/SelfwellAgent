"""一次性脚本：dev DB 验证 report.photos / directions / tags 拍扁结果。

用法：
    cd backend && .venv/Scripts/python.exe scripts/flatten_old_reports.py --dry-run
    cd backend && .venv/Scripts/python.exe scripts/flatten_old_reports.py --apply

本脚本与 alembic migration ``0002_flatten_report_jsonb`` 逻辑一致；用于本地 dev 验证。
生产统一走 alembic upgrade。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# 把 backend/ 加到 sys.path（与 conftest.py 一致）
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _flatten_jsonb(raw: object) -> object:
    """拍扁 ``{"items": [...]}`` → ``[...]``。"""
    if isinstance(raw, dict) and "items" in raw:
        items = raw["items"]
        return items if isinstance(items, list) else []
    return raw


async def _scan(dry_run: bool) -> int:
    from sqlalchemy import text

    from app.db.session import get_session

    changes = 0
    async for session in get_session():
        rows = (
            await session.execute(
                text(
                    "SELECT id, photos, directions, tags "
                    "FROM reports WHERE deleted_at IS NULL"
                )
            )
        ).fetchall()
        for row in rows:
            report_id, photos, directions, tags = row
            new_photos = _flatten_jsonb(photos)
            new_directions = _flatten_jsonb(directions)
            new_tags = _flatten_jsonb(tags)
            if (
                new_photos != photos
                or new_directions != directions
                or new_tags != tags
            ):
                changes += 1
                print(f"[change] report_id={report_id}")
                print(f"  photos:     {photos}  →  {new_photos}")
                print(f"  directions: {directions}  →  {new_directions}")
                print(f"  tags:       {tags}  →  {new_tags}")
                if not dry_run:
                    await session.execute(
                        text(
                            "UPDATE reports "
                            "SET photos = CAST(:photos AS jsonb), "
                            "directions = CAST(:directions AS jsonb), "
                            "tags = CAST(:tags AS jsonb) "
                            "WHERE id = :rid"
                        ),
                        {
                            "photos": _to_jsonb(new_photos),
                            "directions": _to_jsonb(new_directions),
                            "tags": _to_jsonb(new_tags),
                            "rid": str(report_id),
                        },
                    )
        if not dry_run:
            await session.commit()
        break
    return changes


def _to_jsonb(value: object) -> str:
    """转 JSON 字符串（由 PG CAST 解析为 jsonb）。"""
    import json

    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Flatten reports JSONB nested lists")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="默认 dry-run；只打印不写入。",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="真写入 DB（覆盖 dry-run 默认）。",
    )
    args = parser.parse_args()
    dry_run = not args.apply
    changes = asyncio.run(_scan(dry_run=dry_run))
    print(f"\n[summary] changed={changes} dry_run={dry_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
