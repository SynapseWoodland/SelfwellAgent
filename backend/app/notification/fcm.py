"""FCM 推送通道（Sprint 0 占位）。

真源：``docs/spec/facts-anchor.md`` §8。Sprint 0 仅签名；Sprint 5 SF5 e2e 真接入。
"""

from __future__ import annotations

from app.notification.base import NotificationChannel


class FcmChannel(NotificationChannel):
    """Android Firebase Cloud Messaging。"""

    channel_name = "fcm"

    def __init__(self, server_key: str = "", project_id: str = "") -> None:
        self._server_key = server_key
        self._project_id = project_id

    async def send(
        self,
        *,
        target: str,
        title: str,
        body: str,
        trace_id: str | None = None,
    ) -> bool:
        raise NotImplementedError("FcmChannel.send 待 Sprint 5 SF5 e2e 接入")


__all__ = ["FcmChannel"]
