r"""Unit tests for assistant_service.send_message_stream end-frame persistence.

Source:
  - Stream Y / PR-A2 worker Y decision 3: ``on end`` writes assistant_msg in one transaction.
  - docs/data/data-dictionary.md section D.4 ai_messages DDL.
  - backend/app/services/ai_messages_crud.py::persist_assistant_message.

Coverage:
  1. Normal end -> ai_messages row appended, safety_passed=True,
     persona_state/directions written to safety_violations JSONB.
  2. medical_guarded end -> ai_messages row appended, safety_passed=False.
  3. End reply_text and directions are written correctly.

Implementation:
  - send_message_stream is an async generator; iterate
    ``async for chunk in send_message_stream(...)`` and parse each chunk as one
    SSE frame (matches backend ``_sse_pack`` shape: ``event: <name>\ndata: <json>\n\n``).
  - Find the end frame and assert ``data.ai_msg_id`` field.
  - Inspect the last ``session.add`` call (AsyncMock-injected) to assert
    AIMessage fields (safety_passed / safety_violations / content / etc.).
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.ai_messages import AIMessage
from app.services.assistant_service import send_message_stream


def _scalar_result(value: Any) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _make_ai_session(
    *,
    session_id: str = "11111111-1111-4111-8111-111111111111",
    user_id: str = "22222222-2222-4222-8222-222222222222",
    message_count: int = 0,
) -> MagicMock:
    s = MagicMock()
    s.id = session_id
    s.user_id = user_id
    s.user_active = True
    s.closed_at = None
    s.message_count = message_count
    s.persona_state_start = "warm"
    s.persona_state_end = "warm"
    s.total_llm_cost = Decimal("0")
    return s


def _parse_sse_frame(frame: str) -> tuple[str | None, Any]:
    """简单 SSE 帧解析（与后端 _sse_pack 同形）。"""
    event: str | None = None
    data_lines: list[str] = []
    for raw_line in frame.split("\n"):
        line = raw_line.replace("\r", "")
        if not line or line.startswith(":"):
            continue
        if ":" not in line:
            continue
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            event = value
        elif field == "data":
            data_lines.append(value)
    if event is None or not data_lines:
        return None, None
    raw = "\n".join(data_lines)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return event, parsed


async def _collect_sse(agen: Any) -> list[tuple[str | None, Any]]:
    """收集 async generator 输出的所有 SSE 帧。"""
    frames: list[tuple[str | None, Any]] = []
    async for chunk in agen:
        if not isinstance(chunk, str):
            continue
        for piece in chunk.split("\n\n"):
            if not piece.strip():
                continue
            event, data = _parse_sse_frame(piece)
            frames.append((event, data))
    return frames


def _find_ai_message_added(session: AsyncMock, role: str = "assistant") -> AIMessage:
    """在 session.add 的所有调用中找到最新一条 role 匹配的 AIMessage。"""
    for call in reversed(session.add.call_args_list):
        obj = call.args[0]
        if isinstance(obj, AIMessage) and obj.role == role:
            return obj
    raise AssertionError(
        f"未在 session.add 调用中找到 role={role} 的 AIMessage；"
        f"实际调用对象={[c.args[0].__class__.__name__ for c in session.add.call_args_list]}"
    )


# ---------------------------------------------------------------------------
# 1. Normal end -> safety_passed=True + directions/persona_state in JSONB
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_message_stream_end_persists_assistant_msg_safety_passed_true() -> None:
    user_id = "22222222-2222-4222-8222-222222222222"
    ai_session = _make_ai_session()
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()

    frames = await _collect_sse(
        send_message_stream(
            session,
            user_id=user_id,
            session_id="11111111-1111-4111-8111-111111111111",
            text="hi today my neck is stiff",
        )
    )

    end_events = [d for ev, d in frames if ev == "end"]
    assert len(end_events) == 1
    end_data = end_events[0]
    assert end_data["ok"] is True
    assert "ai_msg_id" in end_data, "end 帧必须携带 ai_msg_id（Stream Y 决策 3）"
    assert not end_data.get("medical_guarded")

    assistant_msg = _find_ai_message_added(session, role="assistant")
    assert assistant_msg.role == "assistant"
    assert assistant_msg.safety_passed is True
    # V1.1.1：chat 路径落库 llm_model 由 LLM 链路决定（text-llm 或 static-fallback）
    assert assistant_msg.llm_model in {"text-llm", "static-fallback"}, assistant_msg.llm_model
    assert assistant_msg.session_id == ai_session.id
    assert assistant_msg.safety_violations is not None
    assert "persona_state" in assistant_msg.safety_violations


# ---------------------------------------------------------------------------
# 2. medical_guarded end -> safety_passed=False + medical_guarded metadata
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_message_stream_end_persists_medical_guarded_safety_passed_false() -> None:
    user_id = "22222222-2222-4222-8222-222222222222"
    ai_session = _make_ai_session()
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()

    frames = await _collect_sse(
        send_message_stream(
            session,
            user_id=user_id,
            session_id="11111111-1111-4111-8111-111111111111",
            text="\u6211\u7684\u75c5\u9700\u8981\u6253\u9488\u6cbb\u7597\uff0c\u53bb\u533b\u9662\uff1f",
        )
    )

    end_events = [d for ev, d in frames if ev == "end"]
    assert len(end_events) == 1
    end_data = end_events[0]
    assert end_data.get("medical_guarded") is True
    assert "ai_msg_id" in end_data

    assistant_msg = _find_ai_message_added(session, role="assistant")
    assert assistant_msg.role == "assistant"
    # Decision 3 + TBC-009 §10.4 #9: medical_guarded -> safety_passed must be False.
    assert assistant_msg.safety_passed is False
    assert assistant_msg.safety_violations is not None
    assert assistant_msg.safety_violations.get("medical_guarded") is True
    assert "persona_state" in assistant_msg.safety_violations


# ---------------------------------------------------------------------------
# 3. reply_text + directions content correctness
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_message_stream_end_reply_text_and_directions_written() -> None:
    user_id = "22222222-2222-4222-8222-222222222222"
    ai_session = _make_ai_session()
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()

    frames = await _collect_sse(
        send_message_stream(
            session,
            user_id=user_id,
            session_id="11111111-1111-4111-8111-111111111111",
            text="my shoulders are tight, please help me check",
        )
    )

    end_data = next(d for ev, d in frames if ev == "end")
    reply = end_data["reply"]
    assert isinstance(reply, str) and len(reply) > 0
    assert "ai_msg_id" in end_data

    assistant_msg = _find_ai_message_added(session, role="assistant")
    assert assistant_msg.content == reply
    assert assistant_msg.token_count == len(reply)
    # V1.1.1：chat 路径只把 persona_state 写入 safety_violations；
    # directions 现在属于 context_photos 分面（smart_analyze 路径）
    sv = assistant_msg.safety_violations
    assert isinstance(sv, dict) and "persona_state" in sv
