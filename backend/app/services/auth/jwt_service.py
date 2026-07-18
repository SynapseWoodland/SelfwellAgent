"""JWT 业务服务层。

封装 ``app.auth.jwt_handler`` 的原始 sign/decode，并在 service 层加入：
- user_id 格式校验（UUID v7 字符串）
- 业务上下文（platform / openid_mp / openid_app）注入到 claims
- 用户级「主动失效」机制（M8/M10/M1 共用 Redis 黑名单 key prefix）

真源：``docs/spec/TDS-M1-wechat-login.md`` §4 + §5。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.auth.jwt_handler import (
    JWTError,
    JWTExpiredError,
    decode_token,
    sign_access_token,
)
from app.conf.app_config import app_config
from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.errors.codes import (
    E_AUTH_TOKEN_INVALID,
    E_USER_INVALID_INPUT,
)

if TYPE_CHECKING:
    pass


# JWT 默认过期秒数 = 7 天（M1-FR-04 + facts-anchor §4）
DEFAULT_EXPIRES_SECONDS = 7 * 24 * 60 * 60


class JWTSignError(SelfwellError):
    """JWT 签发失败（如 secret_key 未配置）。"""

    code: str = E_AUTH_TOKEN_INVALID
    message_zh: str = "登录凭证签发失败"
    message_en: str = "Failed to sign access token"
    severity = "PERMANENT"
    http_status = 500


def _validate_user_id(user_id: str) -> str:
    """校验 user_id 是合法 UUID 字符串。"""
    if not user_id or len(user_id) < 16:
        raise UserInputError(
            "user_id 不合法",
            code=E_USER_INVALID_INPUT,
            http_status=400,
            field="user_id",
        )
    return user_id


def issue_token(  # noqa: PLR0913  issue_token needs 6 kw-only params
    *,
    user_id: str,
    platform: str = "wx_mp",
    openid_mp: str | None = None,
    openid_app: str | None = None,
    unionid: str | None = None,
    expires_seconds: int = DEFAULT_EXPIRES_SECONDS,
) -> tuple[str, int]:
    """签发 access token。

    Args:
        user_id: 用户 UUID 字符串。
        platform: 当前激活端（``wx_mp`` / ``ios`` / ``android`` / ``harmony``）。
        openid_mp: 小程序端 openid（跨端打通）。
        openid_app: APP 端 openid。
        unionid: 跨端打通 key。
        expires_seconds: 过期秒数（默认 7 天）。

    Returns:
        ``(token, expires_in)`` —— 业务层可直接返回给前端。

    Raises:
        UserInputError: user_id 不合法。
        JWTSignError: 签发失败。

    """
    _validate_user_id(user_id)
    expires_minutes = max(1, expires_seconds // 60)
    extra_claims: dict[str, object] = {"platform": platform}
    if openid_mp:
        extra_claims["openid_mp"] = openid_mp
    if openid_app:
        extra_claims["openid_app"] = openid_app
    if unionid:
        extra_claims["unionid"] = unionid
    try:
        token = sign_access_token(
            user_id=user_id,
            extra_claims=extra_claims,
            expires_minutes=expires_minutes,
        )
    except JWTError as exc:
        logger.exception("jwt_service_sign_failed", user_id=user_id)
        raise JWTSignError() from exc
    return token, expires_seconds


def verify_token(token: str) -> dict[str, object]:
    """解码并校验 JWT 业务层。

    Returns:
        解码后的 payload（``sub`` 必为 user_id 字符串）。

    Raises:
        JWTExpiredError: 过期。
        JWTError: 其它失败。

    """
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


def token_expires_seconds() -> int:
    """返回当前配置下的 token 过期秒数。"""
    return app_config.jwt.access_token_expire_minutes * 60


__all__ = [
    "DEFAULT_EXPIRES_SECONDS",
    "JWTSignError",
    "issue_token",
    "token_expires_seconds",
    "verify_token",
]
