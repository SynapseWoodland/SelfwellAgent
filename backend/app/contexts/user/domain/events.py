"""User Domain Events.

真源：DDD bounded context §三 Domain Event 命名规范 + §十二 12 个核心 Event
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class UserDomainEvent:
    """所有 User Domain Event 基类。

    字段强制：
    - event_name: str（事件类型名）
    - user_id: str（跨 Context 引用）
    - occurred_at: datetime（时间戳）
    """

    event_name: str
    user_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class UserRegisteredEvent(UserDomainEvent):
    """用户注册成功事件（微信/手机号首次登录）。"""

    unionid: str = ""
    platform: str = "wx_mp"
    trigger: str = "wx_login"


@dataclass(frozen=True, slots=True)
class UserActivatedEvent(UserDomainEvent):
    """用户档案完善，draft → active 事件。"""

    trigger: str = "profile_complete"


@dataclass(frozen=True, slots=True)
class UserDeactivatedEvent(UserDomainEvent):
    """用户注销/封禁事件。"""

    trigger: str = ""


@dataclass(frozen=True, slots=True)
class UserConsentGrantedEvent(UserDomainEvent):
    """用户授权隐私政策事件。"""

    consent_type: str = ""


__all__ = [
    "UserActivatedEvent",
    "UserConsentGrantedEvent",
    "UserDeactivatedEvent",
    "UserDomainEvent",
    "UserRegisteredEvent",
]
