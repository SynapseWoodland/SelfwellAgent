"""Flatten report jsonb nested ``{"items": [...]}`` → list.

迁移真源：Sprint 2026-07-07 M2 修复
- ``reports.photos`` / ``reports.directions`` / ``reports.tags`` 从 ``{"items": [...]}``
  拍扁为 ``list``。
- 老数据 ``tags`` 可能是 ``list[str]`` 或 ``{"items": list[str]}`` 两种形态，统一拍扁。

兼容：保留 ``video_id`` 字段读取（旧 Sprint 2 字段），新写入统一用 ``video_url``。

注意：本迁移幂等；可重复运行。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by alembic.
revision: str = "0002_flatten_report_jsonb"
down_revision: str | None = "0001_initial_v13_locked"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _flatten_jsonb(raw: object) -> object:
    """拍扁 ``{"items": [...]}`` → ``[...]``。"""
    if isinstance(raw, dict) and "items" in raw:
        items = raw["items"]
        return items if isinstance(items, list) else []
    return raw


def upgrade() -> None:
    """把 ``reports.photos`` / ``reports.directions`` / ``reports.tags`` 拍扁为 list。

    实现：PostgreSQL ``jsonb_typeof`` 判断 → ``jsonb_set`` 替换。
    """
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, photos, directions, tags FROM reports WHERE deleted_at IS NULL")
    ).fetchall()

    for row in rows:
        report_id, photos, directions, tags = row
        new_photos = _flatten_jsonb(photos)
        new_directions = _flatten_jsonb(directions)
        new_tags = _flatten_jsonb(tags)
        # 仅在确实发生变化时才 update（避免无谓写）
        if (
            new_photos != photos
            or new_directions != directions
            or new_tags != tags
        ):
            bind.execute(
                sa.text(
                    """
                    UPDATE reports
                    SET photos = CAST(:photos AS jsonb),
                        directions = CAST(:directions AS jsonb),
                        tags = CAST(:tags AS jsonb)
                    WHERE id = :rid
                    """
                ).bindparams(
                    postgresql.jsonb(),
                    postgresql.jsonb(),
                    postgresql.jsonb(),
                ),
                {
                    "photos": sa.JSONB().bind_processor(dialect=bind.dialect)(
                        None, new_photos
                    ),
                    "directions": sa.JSONB().bind_processor(dialect=bind.dialect)(
                        None, new_directions
                    ),
                    "tags": sa.JSONB().bind_processor(dialect=bind.dialect)(None, new_tags),
                    "rid": str(report_id),
                },
            )


def downgrade() -> None:
    """回滚：把 list 重新包成 ``{"items": [...]}``（仅 MVP 调试用，生产慎用）。"""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, photos, directions, tags FROM reports WHERE deleted_at IS NULL")
    ).fetchall()
    for row in rows:
        report_id, photos, directions, tags = row
        if isinstance(photos, list):
            photos = {"items": photos}
        if isinstance(directions, list):
            directions = {"items": directions}
        if isinstance(tags, list):
            tags = {"items": tags}
        bind.execute(
            sa.text(
                """
                UPDATE reports
                SET photos = CAST(:photos AS jsonb),
                    directions = CAST(:directions AS jsonb),
                    tags = CAST(:tags AS jsonb)
                WHERE id = :rid
                """
            ).bindparams(
                postgresql.jsonb(),
                postgresql.jsonb(),
                postgresql.jsonb(),
            ),
            {
                "photos": sa.JSONB().bind_processor(dialect=bind.dialect)(None, photos),
                "directions": sa.JSONB().bind_processor(dialect=bind.dialect)(None, directions),
                "tags": sa.JSONB().bind_processor(dialect=bind.dialect)(None, tags),
                "rid": str(report_id),
            },
        )


__all__: list[str] = ["down_revision", "downgrade", "revision", "upgrade"]
