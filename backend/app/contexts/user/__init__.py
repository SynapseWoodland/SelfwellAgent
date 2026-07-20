"""User Context — DDD Bounded Context.

从 services/auth/ + services/users/profile_service.py 重构而来。

迁移状态：
- domain/: User Aggregate + UserStatus + Domain Events ✅
- application/: UserApplicationService ✅
- infrastructure/: TokenService + UserRepository ✅
- interfaces/: FastAPI Router ✅
"""

from app.contexts.user.application import UserApplicationService
from app.contexts.user.domain import (
    User,
    UserActivatedEvent,
    UserConsentGrantedEvent,
    UserDeactivatedEvent,
    UserDomainEvent,
    UserRegisteredEvent,
    UserStatus,
    UserStatusMachine,
)
from app.contexts.user.infrastructure import TokenService
from app.contexts.user.interfaces import router

__all__ = [
    "TokenService",
    "User",
    "UserActivatedEvent",
    "UserApplicationService",
    "UserConsentGrantedEvent",
    "UserDeactivatedEvent",
    "UserDomainEvent",
    "UserRegisteredEvent",
    "UserStatus",
    "UserStatusMachine",
    "router",
]
