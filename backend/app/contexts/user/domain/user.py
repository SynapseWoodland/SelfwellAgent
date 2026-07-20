"""User Aggregate Root.

真源：DDD bounded context §二 Aggregate Root 铁律 + db/models/user.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.contexts.user.domain.user_status import UserAggregateProtocol

if TYPE_CHECKING:
    from app.contexts.user.domain.events import UserDomainEvent
    from app.contexts.user.domain.user_status import UserStatus


@dataclass
class User(UserAggregateProtocol):
    """User Aggregate Root。

    约束：
    - 唯一入口：所有修改通过本类方法
    - 事务边界：一个 User 实例 = 一个 Aggregate
    - 跨 Context 引用：只传 ID，不传对象
    - 不变性：方法内校验业务规则

    字段与 User ORM 1:1 对齐（db/models/user.py）。
    """

    id: UUID = field(default_factory=uuid4, repr=False)
    unionid: str = ""
    openid_mp: str | None = None
    openid_app: str | None = None
    phone: str | None = None
    platform: str = "wx_mp"
    nickname: str = ""
    avatar: str = ""
    age_range: str | None = None
    sitting_hours: str | None = None
    focus_parts: dict[str, object] | None = None
    intensity: str | None = None
    preferred_time: str | None = None
    skin_type: str | None = None
    email: str | None = None
    status: str = "draft"

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str = ""
    created_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated_by: str = ""

    _events: list[UserDomainEvent] = field(default_factory=list, repr=False)

    # ─── Domain Methods ────────────────────────────────────────────────────────

    def register(self, *, trigger: str) -> None:
        """注册/创建用户（内部方法，外部通过 UserService 调用）。"""
        self._events.append(
            self._build_event(
                "UserRegisteredEvent",
                user_id=str(self.id),
                unionid=self.unionid,
                platform=self.platform,
                trigger=trigger,
            )
        )

    def complete_profile(self) -> bool:
        """补全档案并检查是否触发 draft → active 转换。

        Returns:
            True 如果触发了状态转换。

        """
        from app.contexts.user.domain.user_status import UserStatusMachine

        if self.status != "draft":
            return False
        if not UserStatusMachine.minimum_profile_complete(self):
            return False
        self.status = UserStatus.ACTIVE.value
        self._events.append(
            self._build_event(
                "UserActivatedEvent",
                user_id=str(self.id),
                trigger="profile_complete",
            )
        )
        return True

    def record_login(self) -> None:
        """记录登录，更新 last_active_at。"""
        now = datetime.now(UTC)
        self.last_active_at = now
        self.last_updated_time = now
        self.last_updated_by = str(self.id)

    def deactivate(self, *, trigger: str) -> None:
        """注销/封禁用户（终态）。"""
        from app.contexts.user.domain.user_status import UserStatus, UserStatusMachine

        if self.status == UserStatus.CHURNED.value:
            return
        UserStatusMachine.transition(UserStatus(self.status), UserStatus.CHURNED, trigger, self.id)
        self.status = UserStatus.CHURNED.value
        self._events.append(
            self._build_event(
                "UserDeactivatedEvent",
                user_id=str(self.id),
                trigger=trigger,
            )
        )

    def grant_consent(self, *, consent_type: str) -> None:
        """记录用户授权。"""
        self._events.append(
            self._build_event(
                "UserConsentGrantedEvent",
                user_id=str(self.id),
                consent_type=consent_type,
            )
        )

    def pop_events(self) -> list[UserDomainEvent]:
        """消费并清空 Domain Events（事务提交后由 Application Service 调用）。"""
        events = list(self._events)
        self._events.clear()
        return events

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _build_event(self, event_name: str, /, **kwargs: object) -> UserDomainEvent:
        from app.contexts.user.domain.events import UserDomainEvent

        return UserDomainEvent(
            event_name=event_name,
            user_id=str(self.id),
            occurred_at=datetime.now(UTC),
            **kwargs,
        )


__all__ = ["User"]
