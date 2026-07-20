"""User Application Service.

编排 Domain Layer + Infrastructure Layer，暴露给 Router 调用。
兼容旧 services/auth/ 和 services/users/profile_service.py 的接口签名。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTError, JWTExpiredError, decode_token
from app.auth.wechat_client import WeChatClient, WeChatClientError
from app.contexts.user.domain import (
    UserStatus,
)
from app.contexts.user.infrastructure.token_service import TokenIssuePayload, TokenService
from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models import User as UserOrm
from app.errors.codes import (
    E_AUTH_CODE_INVALID,
    E_AUTH_PHONE_CODE_EXPIRED,
    E_AUTH_PHONE_CODE_INVALID,
    E_AUTH_TOKEN_INVALID,
    E_AUTH_UNIONID_MISMATCH,
    E_USER_INVALID_ENUM,
    E_USER_INVALID_INPUT,
    E_USER_NOT_FOUND,
)

if TYPE_CHECKING:
    pass

# ─── Platform Enum ────────────────────────────────────────────────────────────

_VALID_PLATFORMS: frozenset[str] = frozenset({"wx_mp", "ios", "android", "harmony"})
_AGE_RANGES: frozenset[str] = frozenset({"18-22", "23-28", "29-35", "36-45", "45+"})
_INTENSITIES: frozenset[str] = frozenset({"轻柔", "适中", "进阶"})
_PREFERRED_TIMES: frozenset[str] = frozenset({"早", "中", "晚", "不固定"})
_SITTING_HOURS_MIN, _SITTING_HOURS_MAX = 0, 24
_FOCUS_PARTS: frozenset[str] = frozenset(
    {"face", "head", "shoulder_neck", "waist", "leg", "overall_look"}
)

# SMS rate limit
SMS_SEND_RATE_LIMIT = 5
SMS_CODE_TTL_SECONDS = 300


# ─── Create User Payload ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class CreateUserPayload:
    """_create_user 参数封装（减少 PLR0913 警告）。"""

    unionid: str
    platform: str
    nickname: str
    avatar: str
    trigger: str
    openid_mp: str | None = None
    openid_app: str | None = None
    phone: str | None = None


# ─── Domain Event Bus ────────────────────────────────────────────────────────

_event_handlers: dict[str, list[Callable[..., object]]] = {}


def _get_event_bus() -> dict[str, list[Callable[..., object]]]:
    return _event_handlers


# ─── Application Service ──────────────────────────────────────────────────────


class UserApplicationService:
    """User Context 应用服务。

    职责：
    - 编排 Domain Layer（User Aggregate）
    - 调用 Infrastructure Layer（Repository、TokenService）
    - 发布 Domain Events

    兼容旧接口：login_via_wx / login_via_phone / get_user_profile / update_user_profile
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._token_service = TokenService()

    # ─── Auth Methods ─────────────────────────────────────────────────────────

    async def wx_login(
        self,
        *,
        code: str,
        client: str,
        nickname: str | None = None,
        avatar: str | None = None,
    ) -> tuple[str, str, bool, str, int]:
        """微信登录主入口。

        Returns:
            (user_id, token, is_new_user, user_status, expires_in)

        """
        # 1. validate platform
        if client not in _VALID_PLATFORMS:
            raise UserInputError(
                "client/platform 非法",
                code=E_USER_INVALID_INPUT,
                http_status=400,
                field="client",
            )

        if not code or len(code) < 10:
            raise UserInputError(
                "code 缺失或过短",
                code=E_USER_INVALID_INPUT,
                http_status=400,
                field="code",
            )

        # 2. code2session
        wx_client = WeChatClient()
        try:
            wx_resp: dict[str, str] = await wx_client.code2session(code)
        except WeChatClientError as exc:
            logger.warning("wx_login_code2session_failed", code=code[:8], error=str(exc))
            raise _map_wx_error(exc) from exc

        openid_mp = wx_resp.get("openid") if client == "wx_mp" else None
        openid_app = wx_resp.get("openid") if client != "wx_mp" else None
        unionid = wx_resp.get("unionid")

        # 3. find or create user
        user_orm = await self._find_user_by_openid(openid_mp, openid_app, unionid)
        is_new = user_orm is None
        if user_orm is None:
            user_orm = await self._create_user(
                CreateUserPayload(
                    unionid=unionid or f"wx_openid_{openid_mp or openid_app or uuid4()}",
                    openid_mp=openid_mp,
                    openid_app=openid_app,
                    platform=client,
                    nickname=nickname or "微信用户",
                    avatar=avatar or "",
                    trigger="wx_login",
                )
            )
        else:
            await self._update_login(user_orm, client, openid_mp, openid_app)

        await self._session.flush()

        # 4. issue token
        token, expires_in = self._token_service.issue(
            TokenIssuePayload(
                user_id=str(user_orm.id),
                platform=client,
                openid_mp=user_orm.openid_mp,
                openid_app=user_orm.openid_app,
                unionid=user_orm.unionid,
            )
        )

        logger.info(
            "wx_login_success",
            user_id=str(user_orm.id),
            platform=client,
            is_new=is_new,
            user_status=user_orm.status,
        )

        return (
            str(user_orm.id),
            token,
            is_new,
            user_orm.status or "draft",
            expires_in,
        )

    async def phone_login(
        self,
        *,
        phone: str,
        code: str,
        expires_at: datetime | None = None,
    ) -> tuple[str, str, bool, str, int]:
        """手机号 + 验证码登录。"""
        # validate phone
        if not phone or len(phone) != 11 or not phone.isdigit():
            raise UserInputError(
                "手机号格式错误",
                code=E_USER_INVALID_INPUT,
                http_status=400,
                field="phone",
            )
        if not code or len(code) < 4 or len(code) > 6 or not code.isdigit():
            raise UserInputError(
                "验证码格式错误",
                code=E_USER_INVALID_INPUT,
                http_status=400,
                field="code",
            )

        if expires_at is not None and expires_at < datetime.now(UTC):
            raise PhoneLoginError(
                "验证码已过期，请重新获取",
                code=E_AUTH_PHONE_CODE_EXPIRED,
                http_status=401,
            )

        # dev code
        dev_code = "0000"
        if code != dev_code:
            logger.warning("phone_login_code_invalid", phone_tail=phone[-4:])
            raise PhoneLoginError(
                "验证码错误",
                code=E_AUTH_PHONE_CODE_INVALID,
                http_status=401,
            )

        # find or create
        user_orm = await self._find_user_by_phone(phone)
        is_new = user_orm is None
        if user_orm is None:
            user_orm = await self._create_user(
                CreateUserPayload(
                    unionid=f"phone_{phone}",
                    phone=phone,
                    platform="wx_mp",
                    nickname=f"用户{phone[-4:]}",
                    avatar="",
                    trigger="phone_login",
                )
            )
        else:
            now = datetime.now(UTC)
            user_orm.last_active_at = now
            user_orm.last_updated_time = now
            user_orm.last_updated_by = str(user_orm.id)

        await self._session.flush()

        token, expires_in = self._token_service.issue(
            TokenIssuePayload(
                user_id=str(user_orm.id),
                platform=user_orm.platform or "wx_mp",
                unionid=user_orm.unionid,
            )
        )

        logger.info(
            "phone_login_success",
            user_id=str(user_orm.id),
            phone_tail=phone[-4:],
            is_new=is_new,
        )

        return (
            str(user_orm.id),
            token,
            is_new,
            user_orm.status or "draft",
            expires_in,
        )

    def verify_token(self, token: str) -> dict[str, object]:
        """解码并校验 JWT。"""
        if not token:
            raise JWTError("token 为空", code=E_AUTH_TOKEN_INVALID)
        try:
            payload = decode_token(token)
        except JWTExpiredError:
            raise
        except JWTError:
            raise
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise JWTError("payload.sub 缺失", code=E_AUTH_TOKEN_INVALID)
        return payload

    # ─── Profile Methods ─────────────────────────────────────────────────────

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """获取用户档案。"""
        stmt = select(UserOrm).where(UserOrm.id == user_id)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ProfileNotFoundError(field="user_id", user_id=user_id)
        return _serialize_user(user)

    async def update_user_profile(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """更新用户档案（首登补全 / 日常修改）。"""
        stmt = select(UserOrm).where(UserOrm.id == user_id)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ProfileNotFoundError(field="user_id", user_id=user_id)

        patch = self._validate_profile(payload)
        now = datetime.now(UTC)
        for k, v in patch.items():
            setattr(user, k, v)
        user.last_active_at = now
        user.last_updated_time = now
        user.last_updated_by = user_id

        # draft → active
        if user.status == "draft" and _has_minimum_profile(user):
            user.status = UserStatus.ACTIVE.value
            logger.info("user_promoted_on_profile_complete", user_id=user_id)

        await self._session.flush()
        return _serialize_user(user)

    def _validate_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """校验首登档案字段。"""
        result: dict[str, Any] = {}

        age_range = _ensure_str(payload.get("age_range"), "age_range")
        if age_range is not None:
            if age_range not in _AGE_RANGES:
                raise ProfileEnumError(
                    "age_range 不在 5 档内",
                    field="age_range",
                    allowed=sorted(_AGE_RANGES),
                )
            result["age_range"] = age_range

        focus_parts = _ensure_list(payload.get("focus_parts"), "focus_parts")
        if focus_parts is not None:
            invalid = [p for p in focus_parts if p not in _FOCUS_PARTS]
            if invalid:
                raise ProfileEnumError(
                    "focus_parts 包含非法部位",
                    field="focus_parts",
                    invalid=invalid,
                )
            result["focus_parts"] = focus_parts

        intensity = _ensure_str(payload.get("intensity"), "intensity")
        if intensity is not None:
            if intensity not in _INTENSITIES:
                raise ProfileEnumError(
                    "intensity 枚举非法",
                    field="intensity",
                    allowed=sorted(_INTENSITIES),
                )
            result["intensity"] = intensity

        preferred_time = _ensure_str(payload.get("preferred_time"), "preferred_time")
        if preferred_time is not None:
            if preferred_time not in _PREFERRED_TIMES:
                raise ProfileEnumError(
                    "preferred_time 枚举非法",
                    field="preferred_time",
                    allowed=sorted(_PREFERRED_TIMES),
                )
            result["preferred_time"] = preferred_time

        sitting_hours = _ensure_str(payload.get("sitting_hours"), "sitting_hours")
        if sitting_hours is not None and sitting_hours != "":
            if not sitting_hours.isdigit():
                raise ProfileEnumError(
                    "sitting_hours 必须是 0-24 的整数",
                    field="sitting_hours",
                )
            value = int(sitting_hours)
            if value < _SITTING_HOURS_MIN or value > _SITTING_HOURS_MAX:
                raise ProfileEnumError(
                    "sitting_hours 超出范围",
                    field="sitting_hours",
                    allowed=[str(i) for i in range(_SITTING_HOURS_MIN, _SITTING_HOURS_MAX + 1)],
                )
            result["sitting_hours"] = sitting_hours

        if not result:
            raise UserInputError(
                "未提供任何档案字段",
                code=E_USER_INVALID_INPUT,
                http_status=400,
                field="payload",
            )
        return result

    # ─── Internal Helpers ─────────────────────────────────────────────────────

    async def _find_user_by_openid(
        self, openid_mp: str | None, openid_app: str | None, unionid: str | None
    ) -> UserOrm | None:
        if openid_mp:
            stmt = select(UserOrm).where(UserOrm.openid_mp == openid_mp)
            result = await self._session.execute(stmt)
            if (u := result.scalar_one_or_none()) is not None:
                return u
        if openid_app:
            stmt = select(UserOrm).where(UserOrm.openid_app == openid_app)
            result = await self._session.execute(stmt)
            if (u := result.scalar_one_or_none()) is not None:
                return u
        if unionid:
            stmt = select(UserOrm).where(UserOrm.unionid == unionid)
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        return None

    async def _find_user_by_phone(self, phone: str) -> UserOrm | None:
        stmt = select(UserOrm).where(UserOrm.phone == phone)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_user(self, payload: CreateUserPayload) -> UserOrm:
        now = datetime.now(UTC)
        new_user = UserOrm(
            id=uuid4(),
            unionid=payload.unionid,
            openid_mp=payload.openid_mp,
            openid_app=payload.openid_app,
            phone=payload.phone,
            platform=payload.platform,
            nickname=payload.nickname,
            avatar=payload.avatar,
            status="draft",
            created_at=now,
            last_active_at=now,
            created_by=str(uuid4()),
            created_time=now,
            last_updated_time=now,
            last_updated_by=str(uuid4()),
            version=0,
        )
        self._session.add(new_user)
        await self._session.flush()
        logger.info(
            "user_created",
            user_id=str(new_user.id),
            platform=payload.platform,
            trigger=payload.trigger,
            is_new=True,
        )
        return new_user

    async def _update_login(
        self,
        user: UserOrm,
        platform: str,
        openid_mp: str | None,
        openid_app: str | None,
    ) -> None:
        now = datetime.now(UTC)
        user.platform = platform
        user.last_active_at = now
        user.last_updated_time = now
        user.last_updated_by = str(user.id)
        if openid_mp and user.openid_mp != openid_mp:
            user.openid_mp = openid_mp
        if openid_app and user.openid_app != openid_app:
            user.openid_app = openid_app


# ─── Error Classes ───────────────────────────────────────────────────────────


class WxLoginError(SelfwellError):
    code: str = E_AUTH_CODE_INVALID
    message_zh: str = "微信授权失败"
    message_en: str = "WeChat login failed"
    severity = "USER_ERROR"
    http_status = 401


class UnionidMismatchError(WxLoginError):
    code: str = E_AUTH_UNIONID_MISMATCH
    message_zh: str = "微信 unionid 解密失败，请重试"
    message_en: str = "Failed to decrypt WeChat unionid"


class PhoneLoginError(SelfwellError):
    code: str = E_AUTH_PHONE_CODE_INVALID
    message_zh: str = "手机号验证码登录失败"
    message_en: str = "Phone login failed"
    severity = "USER_ERROR"
    http_status = 401


class ProfileNotFoundError(SelfwellError):
    code: str = E_USER_NOT_FOUND
    message_zh: str = "用户不存在"
    message_en: str = "User not found"
    http_status = 404


class ProfileEnumError(SelfwellError):
    code: str = E_USER_INVALID_ENUM
    message_zh: str = "字段值不在允许范围内"
    message_en: str = "Field value not in allowed enum set"
    http_status = 400


# ─── Helper Functions ────────────────────────────────────────────────────────


def _ensure_str(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProfileEnumError(f"{field} 必须是字符串", field=field)
    return value


def _ensure_list(value: object, field: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ProfileEnumError(f"{field} 必须是列表", field=field)
    return [str(v) for v in value]


def _map_wx_error(exc: WeChatClientError) -> WxLoginError:
    return WxLoginError(
        "微信授权码无效或已过期",
        code=exc.code,
        http_status=exc.http_status,
    )


def _cache_int(cache: dict[str, object], key: str, default: int = 0) -> int:
    """从 JSONB cache 字段安全提取 int（mypy strict 兼容）。"""
    val = cache.get(key, default)
    if isinstance(val, int):
        return val
    if isinstance(val, (float, str)):
        return int(val)
    return default


def _serialize_user(user: UserOrm) -> dict[str, Any]:
    """User ORM → 响应 dict。"""
    cache = user.report_cache if isinstance(user.report_cache, dict) else {}
    return {
        "user_id": str(user.id),
        "user_id_pseudo": str(user.id),
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
        "avatar_url": user.avatar or "",
        "age_range": user.age_range,
        "focus_parts": user.focus_parts or [],
        "intensity": user.intensity,
        "preferred_time": user.preferred_time,
        "sitting_hours": user.sitting_hours,
        "push_channel": user.push_channel,
        "email": user.email,
        "phone": user.phone,
        "status": user.status or "draft",
        "current_streak_days": _cache_int(cache, "streak_days"),
        "fragments": _cache_int(cache, "fragments"),
        "version": user.version,
        "registered_at": user.created_at.isoformat() if user.created_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        "badges_summary": {
            "total_unlocked": 0,
            "total_codes": 6,
            "latest_unlocked": None,
        },
        "streak_days": _cache_int(cache, "streak_days"),
    }


def _has_minimum_profile(user: UserOrm) -> bool:
    """检查 5 字段是否齐全（与 profile_service._has_minimum_profile 行为一致）。"""
    return bool(
        user.age_range
        and user.focus_parts
        and user.intensity
        and user.preferred_time
        and user.sitting_hours
    )


__all__ = [
    "SMS_CODE_TTL_SECONDS",
    "SMS_SEND_RATE_LIMIT",
    "PhoneLoginError",
    "ProfileEnumError",
    "ProfileNotFoundError",
    "UnionidMismatchError",
    "UserApplicationService",
    "WxLoginError",
]
