"""微信订阅消息通道（Sprint 0 占位）。

真源：``docs/spec/facts-anchor.md`` §8 + ``.env`` WX_MP_TEMPLATE_ID。
Sprint 0 仅签名接口；Sprint 1+ M1/M4 推送时真接入微信 API。
"""

from __future__ import annotations

from app.notification.base import NotificationChannel


class WxSubscribeChannel(NotificationChannel):
    """微信小程序订阅消息（``wx.requestSubscribeMessage`` 后端落地）。"""

    channel_name = "wx_subscribe"

    def __init__(self, mp_appid: str = "", mp_secret: str = "", template_id: str = "") -> None:
        self._mp_appid = mp_appid
        self._mp_secret = mp_secret
        self._template_id = template_id

    async def send(
        self,
        *,
        target: str,
        title: str,
        body: str,
        trace_id: str | None = None,
    ) -> bool:
        raise NotImplementedError(
            "WxSubscribeChannel.send 待 Sprint 1 M1 + Sprint 3 M4 接入微信 API"
        )


__all__ = ["WxSubscribeChannel"]
