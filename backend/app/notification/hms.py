"""华为 Push Kit（HMS Core）推送通道（Sprint 0 占位）。

真源：``docs/spec/facts-anchor.md`` §8 + ADR-0010。
"""

from __future__ import annotations

from app.notification.base import NotificationChannel


class HmsChannel(NotificationChannel):
    """华为 Push Kit 推送（鸿蒙端）。"""

    channel_name = "hms"

    def __init__(self, app_id: str = "", app_secret: str = "") -> None:
        self._app_id = app_id
        self._app_secret = app_secret

    async def send(
        self,
        *,
        target: str,
        title: str,
        body: str,
        trace_id: str | None = None,
    ) -> bool:
        raise NotImplementedError("HmsChannel.send 待 Sprint 5 SF5 e2e 接入")


__all__ = ["HmsChannel"]
