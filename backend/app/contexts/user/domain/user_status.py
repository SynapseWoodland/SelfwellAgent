"""User Status Value Object + State Machine.

真源：DDD bounded context §九 Persona 4 态机 + TDS-M1 §3.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID


class UserStatus(StrEnum):
    """用户生命周期状态枚举。"""

    DRAFT = "draft"  # 草稿（24h 内未完善档案）
    ACTIVE = "active"  # 正式用户（5 字段齐全）
    CHURNED = "churned"  # 流失（主动注销 / 风控封禁）


class InvalidStatusTransitionError(Exception):
    """非法状态转换。"""

    pass


@dataclass(frozen=True, slots=True)
class UserStatusTransition:
    """单次状态变更记录。"""

    from_status: UserStatus
    to_status: UserStatus
    trigger: str
    user_id: UUID
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class UserStatusMachine:
    """User Status 状态机（DDD §九强约束）。"""

    _LEGAL_TRANSITIONS: ClassVar[dict[UserStatus, frozenset[UserStatus]]] = {
        UserStatus.DRAFT: frozenset({UserStatus.ACTIVE, UserStatus.CHURNED}),
        UserStatus.ACTIVE: frozenset({UserStatus.CHURNED}),
        UserStatus.CHURNED: frozenset(),  # 终态，不可再转
    }

    @classmethod
    def can_transition(cls, current: UserStatus, target: UserStatus) -> bool:
        """检查是否允许状态转换。"""
        return target in cls._LEGAL_TRANSITIONS.get(current, frozenset())

    @classmethod
    def transition(
        cls, current: UserStatus, target: UserStatus, trigger: str, user_id: UUID
    ) -> UserStatusTransition:
        """执行状态转换，失败抛 InvalidStatusTransitionError。"""
        if not cls.can_transition(current, target):
            raise InvalidStatusTransitionError(
                f"illegal transition {current.value} -> {target.value} (trigger={trigger})"
            )
        return UserStatusTransition(
            from_status=current,
            to_status=target,
            trigger=trigger,
            user_id=user_id,
        )

    @classmethod
    def minimum_profile_complete(cls, user: UserAggregateProtocol) -> bool:
        """检查 5 字段是否齐全（draft → active 条件）。"""
        return bool(
            user.age_range
            and user.focus_parts
            and user.intensity
            and user.preferred_time
            and user.sitting_hours
        )


class UserAggregateProtocol:
    """User Aggregate Root 协议（Domain 层不依赖 ORM）。

    仅用于类型注解，不参与运行时逻辑。
    """

    id: UUID
    status: str
    age_range: str | None
    focus_parts: dict[str, object] | None
    intensity: str | None
    preferred_time: str | None
    sitting_hours: str | None


__all__ = [
    "InvalidStatusTransitionError",
    "UserAggregateProtocol",
    "UserStatus",
    "UserStatusMachine",
    "UserStatusTransition",
]
