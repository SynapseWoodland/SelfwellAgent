"""APNs 推送通道（Sprint 0 占位）。

真源：``docs/spec/facts-anchor.md`` §8。Sprint 0 仅签名；Sprint 5 SF5 e2e 真接入。
"""

from __future__ import annotations

from app.notification.base import NotificationChannel


class ApnsChannel(NotificationChannel):
    """iOS APNs 推送（firebase_messaging bridge）。"""

    channel_name = "apns"

    def __init__(self, certificate_path: str = "", team_id: str = "") -> None:
        self._certificate_path = certificate_path
        self._team_id = team_id

    async def send(
        self,
        *,
        target: str,
        title: str,
        body: str,
        trace_id: str | None = None,
    ) -> bool:
        raise NotImplementedError("ApnsChannel.send 待 Sprint 5 SF5 e2e 接入")


__all__ = ["ApnsChannel"]
