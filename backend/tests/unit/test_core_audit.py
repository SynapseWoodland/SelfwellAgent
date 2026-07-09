"""Unit tests for ``app.core.audit.hash_user_id_pseudo`` (M5 ADR-0017 §3.3).

覆盖：
- 相同 user_id + salt → 相同 hash（幂等）
- 不同 user_id → 不同 hash（区分度）
- 输出长度恒为 16 hex
- 自定义 hex_len
- salt 影响输出
- 空 user_id / 非法 hex_len 抛 ValueError
"""

from __future__ import annotations

import pytest

from app.core.audit import DEFAULT_HEX_LEN, hash_user_id_pseudo


def test_same_user_id_same_salt_produces_same_hash() -> None:
    """幂等性：相同输入 → 相同输出。"""
    a = hash_user_id_pseudo("user-123", salt="abc")
    b = hash_user_id_pseudo("user-123", salt="abc")
    assert a == b


def test_different_user_id_produces_different_hash() -> None:
    """区分度：不同 user_id → 不同 hash。"""
    a = hash_user_id_pseudo("user-123", salt="abc")
    b = hash_user_id_pseudo("user-456", salt="abc")
    assert a != b


def test_hash_length_is_default_16_hex() -> None:
    """默认输出长度 16 hex 字符。"""
    h = hash_user_id_pseudo("user-1", salt="s")
    assert len(h) == DEFAULT_HEX_LEN
    assert len(h) == 16
    # 必须全 hex
    int(h, 16)


def test_custom_hex_len() -> None:
    """自定义 hex_len。"""
    h = hash_user_id_pseudo("user-1", salt="s", hex_len=8)
    assert len(h) == 8
    h2 = hash_user_id_pseudo("user-1", salt="s", hex_len=32)
    assert len(h2) == 32


def test_salt_changes_output() -> None:
    """不同 salt → 不同 hash。"""
    a = hash_user_id_pseudo("user-1", salt="salt-a")
    b = hash_user_id_pseudo("user-1", salt="salt-b")
    assert a != b


def test_empty_user_id_raises() -> None:
    """空 user_id → ValueError。"""
    with pytest.raises(ValueError):
        hash_user_id_pseudo("", salt="s")


def test_invalid_hex_len_raises() -> None:
    """非法 hex_len → ValueError。"""
    with pytest.raises(ValueError):
        hash_user_id_pseudo("u", salt="s", hex_len=0)
    with pytest.raises(ValueError):
        hash_user_id_pseudo("u", salt="s", hex_len=65)
    with pytest.raises(ValueError):
        hash_user_id_pseudo("u", salt="s", hex_len=-1)


def test_default_salt_uses_app_config() -> None:
    """不传 salt → 用 app_config.audit.pseudo_salt。两次调用结果一致。"""
    a = hash_user_id_pseudo("user-1")
    b = hash_user_id_pseudo("user-1")
    assert a == b
    assert len(a) == DEFAULT_HEX_LEN


def test_hash_is_hex_only() -> None:
    """输出必须全部 hex 字符（0-9 a-f）。"""
    h = hash_user_id_pseudo("user-x", salt="y", hex_len=64)
    assert all(c in "0123456789abcdef" for c in h)
