"""Flatten ``users.report_cache`` nested ``{"items": [...]}`` → list.

迁移真源：Sprint 2026-07-08 M2 SPD 修复
- ``users.report_cache.directions`` / ``users.report_cache.tags`` 从
  ``{"items": [...]}`` 拍扁为 ``[...]`` 顶层 list。
- 旧 Sprint 2 实现的 ``report_cache`` 把 ``directions``/``tags`` 存为
  ``{"items": [...]}``；运行期 ``_flatten_items`` 兜底会导致 500 兜底分支被命中。

3 阶段路径：
- 阶段 1（本期）：本迁移把存量数据拍扁为 list。
- 阶段 2（保留 2 个 release）：``_flatten_items`` 兜底仍生效，避免漏网数据 500。
- 阶段 3（≥ 2 个 release 后）：删除 ``_flatten_items`` 兜底。

幂等：可重复运行。raw SQL 兼容 ``directions`` / ``tags`` 不是 dict 的情况（直接保留）。

注意：本迁移只处理 ``report_cache``，不动 ``reports`` 表（已有 0002 处理）。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by alembic.
revision: str = "0003_flatten_report_cache"
down_revision: str | None = "0002_flatten_report_jsonb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """把 ``users.report_cache.directions`` / ``tags`` 从 ``{"items": [...]}`` 拍扁。

    实现：PostgreSQL ``jsonb_typeof`` 判断 → 用 ``jsonb_set`` 替换。

    SQL 说明：
    - ``jsonb_typeof(report_cache->'directions') = 'object'``：dict 形态
      （可能是 ``{"items": [...]}``）
    - ``jsonb_typeof(report_cache->'directions'->'items') = 'array'``：items 字段存在且是数组
    - 满足两条件时，用 ``#-`` 运算符删 ``items`` key，提起 value
    """
    bind = op.get_bind()
    # 仅处理 active 用户（deleted_at IS NULL）；report_cache IS NOT NULL
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET report_cache = jsonb_set(
                report_cache #- '{directions}',
                '{directions}',
                report_cache->'directions'->'items',
                false
            )
            WHERE deleted_at IS NULL
              AND report_cache IS NOT NULL
              AND jsonb_typeof(report_cache->'directions') = 'object'
              AND report_cache->'directions' ? 'items'
              AND jsonb_typeof(report_cache->'directions'->'items') = 'array'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET report_cache = jsonb_set(
                report_cache #- '{tags}',
                '{tags}',
                report_cache->'tags'->'items',
                false
            )
            WHERE deleted_at IS NULL
              AND report_cache IS NOT NULL
              AND jsonb_typeof(report_cache->'tags') = 'object'
              AND report_cache->'tags' ? 'items'
              AND jsonb_typeof(report_cache->'tags'->'items') = 'array'
            """
        )
    )


def downgrade() -> None:
    """回滚：把 list 重新包成 ``{"items": [...]}``（仅 MVP 调试用，生产慎用）。

    仅在 ``directions`` / ``tags`` 是 array 时才包回 dict。
    """
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET report_cache = jsonb_set(
                report_cache,
                '{directions}',
                jsonb_build_object('items', report_cache->'directions'),
                true
            )
            WHERE deleted_at IS NULL
              AND report_cache IS NOT NULL
              AND jsonb_typeof(report_cache->'directions') = 'array'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET report_cache = jsonb_set(
                report_cache,
                '{tags}',
                jsonb_build_object('items', report_cache->'tags'),
                true
            )
            WHERE deleted_at IS NULL
              AND report_cache IS NOT NULL
              AND jsonb_typeof(report_cache->'tags') = 'array'
            """
        )
    )


__all__: list[str] = ["down_revision", "downgrade", "revision", "upgrade"]
