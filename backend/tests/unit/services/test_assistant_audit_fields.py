"""Unit tests for ``app.services.assistant_service`` audit fields。

真源：本次 audit 整改
- AISession.created_by = str(user_id)             （会话发起人）
- AISession.last_updated_by = str(user_id)         （创建时即更新）
- AIMessage.user_msg.created_by = str(user_id)    （发消息的人）
- AIMessage.assistant_msg.created_by = str(user_id) （AI 消息由用户对话触发，记用户）

业务决策（已与你确认）：
AI 回复虽然模型生成，但触发原因是用户发消息，所以 audit 字段记用户而不是"assistant"。
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.assistant_service import create_session, send_message


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ─────────────────────────────────────────────────────────────────────────────
# create_session
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_session_audit_fields_use_current_user_id() -> None:
    user_id = "u-chat-1"
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    # entry_card="general" / primary_intent="general" 是历史枚举值，
    # 应被 ENTRY_CARD_COMPAT / PRIMARY_INTENT_COMPAT 兜底映射，不抛错、不 500
    await create_session(session, user_id=user_id, entry_card="general", primary_intent="general")

    ai_session = session.add.call_args[0][0]
    forbidden = {"M5", "m5", "assistant", "system", "chat"}
    assert ai_session.created_by not in forbidden
    assert ai_session.last_updated_by not in forbidden
    assert ai_session.created_by == user_id
    assert ai_session.last_updated_by == user_id


@pytest.mark.asyncio
async def test_create_session_audit_time_is_utc() -> None:
    user_id = "u-1"
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    before = datetime.now(UTC)
    await create_session(session, user_id=user_id)
    after = datetime.now(UTC)

    ai_session = session.add.call_args[0][0]
    assert before <= ai_session.created_time <= after
    assert before <= ai_session.last_updated_time <= after


# ─────────────────────────────────────────────────────────────────────────────
# send_message
# ─────────────────────────────────────────────────────────────────────────────
def _make_ai_session(session_id: str = "s-1", message_count: int = 0) -> MagicMock:
    s = MagicMock()
    s.id = session_id
    s.user_id = "u-1"
    s.user_active = True
    s.closed_at = None
    s.message_count = message_count
    s.persona_state_start = "warm"
    s.persona_state_end = "warm"
    s.total_llm_cost = Decimal("0")
    return s


@pytest.mark.asyncio
async def test_send_message_user_and_assistant_msgs_use_current_user_id() -> None:
    """两条消息（user + assistant）的 audit 字段都是 str(user_id)。"""
    user_id = "u-msg-1"
    ai_session = _make_ai_session()
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()

    await send_message(session, user_id=user_id, session_id="s-1", text="hi 你好")

    # session.add 调用了 2 次：user_msg, assistant_msg
    assert session.add.call_count == 2
    user_msg = session.add.call_args_list[0][0][0]
    assistant_msg = session.add.call_args_list[1][0][0]

    forbidden = {"M5", "m5", "assistant", "system", "ai"}

    # user message
    assert user_msg.role == "user"
    assert user_msg.created_by not in forbidden
    assert user_msg.last_updated_by not in forbidden
    assert user_msg.created_by == user_id
    assert user_msg.last_updated_by == user_id

    # assistant message —— audit 字段记用户
    assert assistant_msg.role == "assistant"
    assert assistant_msg.created_by not in forbidden
    assert assistant_msg.last_updated_by not in forbidden
    assert assistant_msg.created_by == user_id
    assert assistant_msg.last_updated_by == user_id


@pytest.mark.asyncio
async def test_send_message_audit_time_is_utc() -> None:
    user_id = "u-1"
    ai_session = _make_ai_session()
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()

    before = datetime.now(UTC)
    await send_message(session, user_id=user_id, session_id="s-1", text="hi")
    after = datetime.now(UTC)

    user_msg = session.add.call_args_list[0][0][0]
    assert before <= user_msg.created_time <= after
    assert before <= user_msg.last_updated_time <= after
