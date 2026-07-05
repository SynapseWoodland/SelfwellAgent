"""app.auth — 认证模块（Sprint 0 骨架）。"""

from app.auth.jwt_handler import (
    JWTError,
    JWTExpiredError,
    JWTInvalidSignatureError,
    decode_token,
    sign_access_token,
)
from app.auth.wechat_client import WeChatClient, WeChatClientError

__all__ = [
    "JWTError",
    "JWTExpiredError",
    "JWTInvalidSignatureError",
    "WeChatClient",
    "WeChatClientError",
    "decode_token",
    "sign_access_token",
]
