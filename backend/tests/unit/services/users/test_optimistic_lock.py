"""Unit tests for ``app.services.users.optimistic_lock``."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.users.optimistic_lock import (
    OptimisticLockError,
)


class _FakeRow:
    """模拟 SQLAlchemy model 的最小 surface（带 version 字段）。"""


@pytest.mark.asyncio
async def test_update_with_version_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """成功路径：行受影响 = 1。"""
    fake_session = AsyncMock()
    fake_result = MagicMock()
    fake_result.rowcount = 1
    fake_session.execute.return_value = fake_result

    # 构造一个假 model：其 ``.id`` / ``.version`` 属性可被 getattr 访问
    class FakeModel:
        id = None
        version = None

    # 替换 update_with_version 内部使用的 update() 构造
    from unittest.mock import patch

    from app.services.users import optimistic_lock

    with patch.object(optimistic_lock, "update") as mock_update:
        mock_stmt = MagicMock()
        mock_update.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        mock_stmt.execution_options.return_value = mock_stmt

        n = await optimistic_lock.update_with_version(
            fake_session,
            model=FakeModel,
            record_id="rec-1",
            expected_version=3,
            patch={"nickname": "x"},
        )
    assert n == 1


@pytest.mark.asyncio
async def test_update_with_version_conflict() -> None:
    """冲突路径：rowcount=0 → OptimisticLockError。"""
    from unittest.mock import patch

    from app.services.users import optimistic_lock

    fake_session = AsyncMock()
    fake_result = MagicMock()
    fake_result.rowcount = 0
    fake_session.execute.return_value = fake_result

    class FakeModel:
        id = None
        version = None

    with patch.object(optimistic_lock, "update") as mock_update:
        mock_stmt = MagicMock()
        mock_update.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        mock_stmt.execution_options.return_value = mock_stmt

        with pytest.raises(OptimisticLockError):
            await optimistic_lock.update_with_version(
                fake_session,
                model=FakeModel,
                record_id="rec-1",
                expected_version=3,
                patch={"nickname": "x"},
            )
