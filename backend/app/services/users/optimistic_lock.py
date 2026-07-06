"""乐观锁并发控制工具（version 字段）。

真源：``docs/api/openapi.yaml`` ``#/components/schemas/User`` ``version`` 字段
+ User ORM ``version: Mapped[int] = mapped_column(INTEGER, default=0)``。

约定：
- 每次 UPDATE 都让 ``version = version + 1``
- WHERE 条件必须包含 ``version = :expected_version``
- 影响行数为 0 → 抛 ``OptimisticLockError``（HTTP 409）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError
from app.errors.codes import E_GENERAL_CONFLICT

if TYPE_CHECKING:
    pass


class OptimisticLockError(SelfwellError):
    """乐观锁冲突（version 不匹配）。"""

    code: str = E_GENERAL_CONFLICT
    message_zh: str = "记录已被他人修改，请刷新后重试"
    message_en: str = "Record modified by another user, please retry"
    severity = "USER_ERROR"
    http_status = 409


async def update_with_version(  # noqa: PLR0913  optimistic-lock UPDATE needs 6 kwargs
    session: AsyncSession,
    *,
    model: type,
    record_id: object,
    expected_version: int,
    patch: dict[str, object],
    id_column_name: str = "id",
) -> int:
    """带乐观锁的 UPDATE；返回受影响行数。

    Args:
        session: AsyncSession。
        model: ORM 模型类。
        record_id: 主键值。
        expected_version: 客户端提交的 version。
        patch: 待更新字段 dict。
        id_column_name: 主键字段名（默认 ``id``）。

    Returns:
        受影响行数（0 或 1）。

    Raises:
        OptimisticLockError: 0 行受影响（version 已变更）。

    """
    patch_with_version: dict[str, object] = dict(patch)
    patch_with_version["version"] = expected_version + 1
    model_cls: Any = model  # 接受任意 ORM 类
    stmt = (
        update(model_cls)
        .where(getattr(model_cls, id_column_name) == record_id)
        .where(model_cls.version == expected_version)
        .values(**patch_with_version)
        .execution_options(synchronize_session=False)
    )
    result = await session.execute(stmt)
    rowcount = getattr(result, "rowcount", 0) or 0
    if rowcount == 0:
        raise OptimisticLockError()
    return int(rowcount)


__all__ = [
    "OptimisticLockError",
    "update_with_version",
]
