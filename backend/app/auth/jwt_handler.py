"""JWT 签发与校验（Sprint 0 骨架）。

真源：``docs/spec/TDS-M1-wechat-login.md`` + ``app.conf.app_config.JWTConfig`` + ADR-0007。
"""

from __future__ import annotations

import time as _time

import jwt as pyjwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
)

from app.conf.app_config import app_config
from app.core.errors import SelfwellError

__all__ = [
    "JWTError",
    "JWTExpiredError",
    "JWTInvalidSignatureError",
    "decode_token",
    "sign_access_token",
]


# ─────────────────────────────────────────────────────────────────────────────
# §一 域异常（与 coding-standards §九 错误处理规范对齐）
# ─────────────────────────────────────────────────────────────────────────────
class JWTError(SelfwellError):
    """JWT 校验通用失败。"""

    code: str = "E_AUTH_TOKEN_INVALID"
    message_zh: str = "Token 无效"
    message_en: str = "Invalid token"
    severity = "USER_ERROR"
    http_status = 401


class JWTExpiredError(JWTError):
    code: str = "E_AUTH_TOKEN_EXPIRED"
    message_zh: str = "登录已过期，请重新登录"
    message_en: str = "Login expired, please login again"


class JWTInvalidSignatureError(JWTError):
    code: str = "E_AUTH_TOKEN_INVALID"


# ─────────────────────────────────────────────────────────────────────────────
# §二 签发 / 校验
# ─────────────────────────────────────────────────────────────────────────────
def sign_access_token(
    *,
    user_id: str,
    extra_claims: dict[str, object] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """签发 JWT access token。

    Args:
        user_id: 用户 UUID（写入 ``sub`` claim）。
        extra_claims: 自定义 claims（``openid_mp`` / ``unionid`` / ``platform`` 等）。
        expires_minutes: 覆盖默认过期时间（默认 = ``app_config.jwt.access_token_expire_minutes``）。

    Raises:
        PermanentError: ``app_config.jwt.secret_key`` 不足 32 字符时。

    """
    if not app_config.is_jwt_configured:
        raise JWTError(
            "JWT_SECRET_KEY 未配置（必须 ≥ 32 字符）",
            code="E_GENERAL_INTERNAL_ERROR",
            http_status=500,
        )
    now_minutes = expires_minutes or app_config.jwt.access_token_expire_minutes
    now_ts = int(_time.time())
    payload: dict[str, object] = {
        "sub": user_id,
        "type": "access",
        "iat": now_ts,
        "exp": now_ts + now_minutes * 60,
    }
    if extra_claims:
        payload.update(extra_claims)
    token: str = pyjwt.encode(
        payload,
        app_config.jwt.secret_key,
        algorithm=app_config.jwt.algorithm,
    )
    return token


def decode_token(token: str, *, verify_exp: bool = True) -> dict[str, object]:
    """解码并校验 JWT。

    Raises:
        JWTExpiredError: 过期。
        JWTInvalidSignatureError: 签名错误。
        JWTError: 其它错误（malformed / decode error）。

    """
    try:
        payload: dict[str, object] = pyjwt.decode(
            token,
            app_config.jwt.secret_key,
            algorithms=[app_config.jwt.algorithm],
            options={"verify_exp": verify_exp},
        )
        return payload
    except ExpiredSignatureError as exc:
        raise JWTExpiredError() from exc
    except InvalidSignatureError as exc:
        raise JWTInvalidSignatureError() from exc
    except (DecodeError, InvalidTokenError) as exc:
        raise JWTError() from exc
