"""推送通道抽象（Sprint 0 骨架）。

真源：``docs/spec/facts-anchor.md`` §8 + ADR-0008 推送门面 + §十三 §3。

约定：所有推送都从抽象门面走；M9 NotificationFacade 调用各通道。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class NotificationChannel(ABC):
    """推送通道抽象基类。"""

    channel_name: str = "abstract"

    @abstractmethod
    async def send(
        self,
        *,
        target: str,
        title: str,
        body: str,
        trace_id: str | None = None,
    ) -> bool:
        """推送；返回 ``True`` 表示发送成功（投递成功 ≠ 用户已读）。"""


__all__ = ["NotificationChannel"]
