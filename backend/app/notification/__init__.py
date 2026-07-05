"""app.notification — 推送通道 + 邮件兜底（Sprint 0）。"""

from app.notification.apns import ApnsChannel
from app.notification.base import NotificationChannel
from app.notification.email_dm import EmailDmChannel
from app.notification.fcm import FcmChannel
from app.notification.hms import HmsChannel
from app.notification.wx_subscribe import WxSubscribeChannel

__all__ = [
    "ApnsChannel",
    "EmailDmChannel",
    "FcmChannel",
    "HmsChannel",
    "NotificationChannel",
    "WxSubscribeChannel",
]
