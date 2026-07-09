"""Add ``reports.status`` column for async pipeline 状态机。

真源：Sprint 2026-07-08 PR-A1（JobStateStore + Report.status 迁移）。
- ``reports.status`` 新增可空 String(16)，与 ``JobStateStore`` 4 状态（queued /
  running / ready / failed）对齐。
- 同步 LLM 路径不写此列，保持 NULL（向后兼容现有 78 个测试 + 老 report 行）。
- 本迁移 **仅加列**（nullable=True），不回填数据；PR-A2 路由会在 async=true 时写入。

幂等：本迁移 op.add_column 不支持 ``IF NOT EXISTS``（PostgreSQL 9.6+ ``ADD COLUMN
IF NOT EXISTS`` 是方言扩展），重跑会失败 —— alembic 版本表会阻止二次执行，本迁移
默认就是一次性的。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by alembic.
revision: str = "0004_report_status"
down_revision: str | None = "0003_flatten_report_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """加 ``reports.status`` 列（String(16)，nullable=True，默认 NULL）。"""
    op.add_column(
        "reports",
        sa.Column("status", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    """回滚：删 ``reports.status`` 列。"""
    op.drop_column("reports", "status")


__all__: list[str] = ["down_revision", "downgrade", "revision", "upgrade"]
