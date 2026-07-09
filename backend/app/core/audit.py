"""合规审计：HMAC-SHA256 伪 ID 生成。

真源：ADR-0017 §3.3 + ``docs/api/error-codes.md`` 审计事件字段约束。

约定：
- 用 HMAC-SHA256(user_id, salt) 取前 16 hex 字符作为伪 ID（16 hex = 64 bit）
- 同一 (user_id, salt) 始终生成相同伪 ID（用于跨日志关联）
- 不同 user_id 在同一 salt 下几乎不碰撞（生日悖论：64 bit → ~ 4B 才有 50%）
- 盐来自 ``app_config.audit.pseudo_salt``，env 注入 ``AUDIT_PSEUDO_SALT``
- 禁止把 user_id 原值或邮箱/手机号等 PII 直接写入 audit log

测试：
- 相同输入 → 相同输出（幂等）
- 不同 user_id → 不同输出
- 输出长度恒为 16 hex 字符
"""

from __future__ import annotations

import hashlib
import hmac

from app.conf.app_config import app_config

DEFAULT_HEX_LEN: int = 16


def hash_user_id_pseudo(
    user_id: str,
    *,
    salt: str | None = None,
    hex_len: int = DEFAULT_HEX_LEN,
) -> str:
    """把 user_id 哈希成不可逆伪 ID。

    Args:
        user_id: 原始 user_id（UUID / snowflake）。
        salt: HMAC 盐；不传则用 ``app_config.audit.pseudo_salt``。
        hex_len: 返回 hex 字符数（默认 16 = 64 bit）。

    Returns:
        hex 字符串，长度 = ``hex_len``。

    Example:
        >>> a = hash_user_id_pseudo("user-123")
        >>> b = hash_user_id_pseudo("user-123")
        >>> assert a == b
        >>> assert len(a) == 16
        >>> c = hash_user_id_pseudo("user-456")
        >>> assert a != c

    """
    if hex_len <= 0 or hex_len > 64:
        raise ValueError(f"hex_len must be in (0, 64], got {hex_len}")
    if not user_id:
        raise ValueError("user_id must not be empty")
    effective_salt = salt if salt is not None else app_config.audit.pseudo_salt
    digest = hmac.new(
        effective_salt.encode("utf-8"),
        user_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:hex_len]


__all__ = ["DEFAULT_HEX_LEN", "hash_user_id_pseudo"]
