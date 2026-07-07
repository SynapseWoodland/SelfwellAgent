"""手机号验证码登录业务服务层（M1 §4.2，APP 端回退）。

真源：``docs/spec/SPEC-M1-wechat-login.md`` §4.2。

MVP 阶段策略：
- 验证码固定为开发态 ``0000``（.env DEV_SMS_CODE 控制）
- 60s 内同一手机号 ≥ 5 次触发 ``E_USER_SMS_SEND_FREQUENT``（``E_AUTH_LOGIN_FREQUENT``）
- 不接真实短信网关（生产由 M9 推送门面接管）
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models import Feedback  # noqa: F401  trigger mapper configure before User use
from app.db.models.user import User
from app.errors.codes import (
    E_AUTH_LOGIN_FREQUENT,
    E_AUTH_PHONE_CODE_EXPIRED,
    E_AUTH_PHONE_CODE_INVALID,
    E_USER_INVALID_INPUT,
    E_USER_NOT_FOUND,
    E_USER_SMS_SEND_FREQUENT,
)
from app.services.auth.jwt_service import issue_token

# 60s 内同号 ≥ 5 次拒发
SMS_SEND_RATE_LIMIT = 5
# 验证码 5 分钟过期
SMS_CODE_TTL_SECONDS = 300


class PhoneLoginError(SelfwellError):
    """手机号登录业务异常基类。"""

    code: str = E_AUTH_PHONE_CODE_INVALID
    message_zh: str = "手机号验证码登录失败"
    message_en: str = "Phone login failed"
    severity = "USER_ERROR"
    http_status = 401


def _dev_sms_code() -> str:
    """开发态固定验证码（默认 ``0000``）。"""
    return os.getenv("DEV_SMS_CODE", "0000")


def _validate_phone(phone: str) -> str:
    if not phone or len(phone) != 11 or not phone.isdigit():
        raise UserInputError(
            "手机号格式错误",
            code=E_USER_INVALID_INPUT,
            http_status=400,
            field="phone",
        )
    return phone


def _validate_code(code: str) -> str:
    if not code or len(code) < 4 or len(code) > 6 or not code.isdigit():
        raise UserInputError(
            "验证码格式错误",
            code=E_USER_INVALID_INPUT,
            http_status=400,
            field="code",
        )
    return code


async def _find_user_by_phone(session: AsyncSession, phone: str) -> User | None:
    stmt = select(User).where(User.phone == phone)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _create_user_for_phone(
    session: AsyncSession, phone: str, nickname: str | None = None
) -> User:
    now_ts = datetime.now(UTC)
    new_user_id = uuid4()
    new_user = User(
        id=new_user_id,
        unionid=f"phone_{phone}",
        phone=phone,
        platform="wx_mp",
        nickname=nickname or f"用户{phone[-4:]}",
        avatar="",
        status="draft",
        created_at=now_ts,
        last_active_at=now_ts,
        created_by=str(new_user_id),         # 当前创建用户（新 user 自己）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(new_user_id),
        version=0,
    )
    session.add(new_user)
    await session.flush()
    return new_user


async def request_sms_code(phone: str, *, recent_send_count: int = 0) -> None:
    """请求发送短信验证码。

    Args:
        phone: 11 位手机号。
        recent_send_count: 调用方已记录的 60s 内发送次数（外部由 Redis 维护）。

    Raises:
        UserInputError: phone 格式错误。
        PhoneLoginError: 60s 内 ≥ 5 次。

    """
    _validate_phone(phone)
    if recent_send_count >= SMS_SEND_RATE_LIMIT:
        logger.warning("phone_sms_rate_limited", phone_tail=phone[-4:])
        raise PhoneLoginError(
            "短信发送过于频繁，请稍后再试",
            code=E_USER_SMS_SEND_FREQUENT,
            http_status=429,
        )
    logger.info("phone_sms_code_sent", phone_tail=phone[-4:])


async def login_via_phone(
    session: AsyncSession,
    *,
    phone: str,
    code: str,
    expires_at: datetime | None = None,
) -> tuple[str, str, bool, str, int]:
    """手机号 + 验证码登录。

    Args:
        session: DB session。
        phone: 11 位手机号。
        code: 4-6 位验证码。
        expires_at: 验证码过期时间（外部 Redis 维护，None 表示永不过期 — 测试用）。

    Returns:
        ``(user_id, token, is_new_user, user_status, expires_in)``。

    Raises:
        UserInputError: phone / code 格式错误。
        PhoneLoginError: 验证码错误 / 过期 / 频繁。

    """
    _validate_phone(phone)
    _validate_code(code)

    if expires_at is not None and expires_at < datetime.now(UTC):
        raise PhoneLoginError(
            "验证码已过期，请重新获取",
            code=E_AUTH_PHONE_CODE_EXPIRED,
            http_status=401,
        )

    if code != _dev_sms_code():
        logger.warning("phone_login_code_invalid", phone_tail=phone[-4:])
        raise PhoneLoginError(
            "验证码错误",
            code=E_AUTH_PHONE_CODE_INVALID,
            http_status=401,
        )

    user = await _find_user_by_phone(session, phone)
    is_new = user is None
    if user is None:
        user = await _create_user_for_phone(session, phone)
    else:
        user.last_active_at = datetime.now(UTC)
        user.last_updated_time = user.last_active_at
        user.last_updated_by = str(user.id)  # 当前更新用户（自己登录即自己更新）

    await session.flush()

    token, expires_in = issue_token(
        user_id=str(user.id),
        platform=user.platform or "wx_mp",
        unionid=user.unionid,
    )
    logger.info(
        "phone_login_success",
        user_id=str(user.id),
        phone_tail=phone[-4:],
        is_new=is_new,
    )
    return (
        str(user.id),
        token,
        is_new,
        user.status or "draft",
        expires_in,
    )


__all__ = [
    "SMS_CODE_TTL_SECONDS",
    "SMS_SEND_RATE_LIMIT",
    "PhoneLoginError",
    "login_via_phone",
    "request_sms_code",
]


# 抑制未使用导入告警
_ = E_AUTH_LOGIN_FREQUENT
_ = E_USER_NOT_FOUND
