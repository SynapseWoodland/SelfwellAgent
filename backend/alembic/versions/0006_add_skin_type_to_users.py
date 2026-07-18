"""Add ``skin_type`` VARCHAR(10) column to ``users`` (V5.2.1-PR2 T15).

真源：V5.2.1 §3.5 T15：profile 6 字段含 ``skin_type`` 必填对应 User 模型。
- 新增 ``users.skin_type`` VARCHAR(10) nullable 字段。
- V5.2.1 §3.5 枚举待 TDS-M(用户档案) 拍板；本迁移仅建可空列，PR5 前端档案页落档后回填枚举与 CHECK。
- 幂等：与 0005 同（alembic 版本表）。

向下兼容：
- 旧 users 行的 skin_type = NULL（默认）。
- assistant profile dict 中 ``skin_type=None`` 由 Pydantic Optional 接受。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_add_skin_type_to_users"
down_revision: str | None = "0005_add_assistant_profile_to_ai_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``users.skin_type`` VARCHAR(10) nullable column."""
    op.add_column(
        "users",
        sa.Column("skin_type", sa.VARCHAR(10), nullable=True),
    )


def downgrade() -> None:
    """回滚：删 ``skin_type`` 列。"""
    op.drop_column("users", "skin_type")


__all__: list[str] = ["down_revision", "downgrade", "revision", "upgrade"]
