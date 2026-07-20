"""Token Service — Infrastructure Layer.

封装 JWT 签发/校验，从 auth/jwt_handler 迁入。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.auth.jwt_handler import (
    JWTError,
    sign_access_token,
)
from app.conf.app_config import app_config

# JWT 默认 7 天（M1-FR-04）
DEFAULT_EXPIRES_SECONDS = 7 * 24 * 60 * 60


class JWTSignError(Exception):
    """JWT 签发失败。"""

    pass


@dataclass(frozen=True)
class TokenIssuePayload:
    """TokenService.issue 参数封装（减少 PLR0913）。"""

    user_id: str
    platform: str = "wx_mp"
    openid_mp: str | None = None
    openid_app: str | None = None
    unionid: str | None = None
    expires_seconds: int = DEFAULT_EXPIRES_SECONDS


class TokenService:
    """JWT Token 基础设施服务。"""

    def issue(self, payload: TokenIssuePayload) -> tuple[str, int]:
        """签发 access token。

        Returns:
            (token, expires_in)

        """
        if not payload.user_id or len(payload.user_id) < 16:
            raise ValueError(f"user_id 不合法: {payload.user_id}")
        expires_minutes = max(1, payload.expires_seconds // 60)
        extra_claims: dict[str, object] = {"platform": payload.platform}
        if payload.openid_mp:
            extra_claims["openid_mp"] = payload.openid_mp
        if payload.openid_app:
            extra_claims["openid_app"] = payload.openid_app
        if payload.unionid:
            extra_claims["unionid"] = payload.unionid
        try:
            token = sign_access_token(
                user_id=payload.user_id,
                extra_claims=extra_claims,
                expires_minutes=expires_minutes,
            )
        except JWTError as exc:
            raise JWTSignError(f"JWT 签发失败: {exc}") from exc
        return token, payload.expires_seconds

    def token_expires_seconds(self) -> int:
        """返回当前配置下的 token 过期秒数。"""
        return app_config.jwt.access_token_expire_minutes * 60


__all__ = ["DEFAULT_EXPIRES_SECONDS", "JWTSignError", "TokenIssuePayload", "TokenService"]
