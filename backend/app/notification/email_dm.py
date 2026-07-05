"""邮件兜底推送（DirectMail · Sprint 0 占位）。

真源：``docs/spec/facts-anchor.md`` §8 + ``.env`` ALIYUN_DM_*。
``alibabacloud-dm20151123`` SDK 已在 pyproject.toml 声明。
Sprint 0 仅签名；Sprint 4/5 SF5 真接入。
"""

from __future__ import annotations

from app.notification.base import NotificationChannel


class EmailDmChannel(NotificationChannel):
    """阿里云 DirectMail 邮件推送（4 端推送全失败时的兜底）。"""

    channel_name = "email"

    def __init__(
        self,
        *,
        access_key_id: str = "",
        access_key_secret: str = "",
        region: str = "cn-hangzhou",
    ) -> None:
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._region = region

    async def send(
        self,
        *,
        target: str,
        title: str,
        body: str,
        trace_id: str | None = None,
    ) -> bool:
        raise NotImplementedError("EmailDmChannel.send 待 Sprint 5 SF5 接入")


__all__ = ["EmailDmChannel"]
