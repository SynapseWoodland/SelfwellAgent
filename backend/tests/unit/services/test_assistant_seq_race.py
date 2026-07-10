r"""Unit tests for assistant_service.send_message_stream seq race condition fix.

真源：PR-F.1 Step 1.5 + V5.0 V5.1 执行计划 §2.2 Step 1.5。

修复目标：
  - send_message_stream 第一条 SELECT 带 SELECT FOR UPDATE 行锁，
    避免并发请求读到同一个 message_count 算出相同 seq。
  - IntegrityError（seq 唯一约束冲突）兜底捕获，
    返回限流 SSE error 帧，前端可 toast 并重试。

覆盖：
  1. SELECT 语句携带 with_for_update()（FOR UPDATE 锁）。
  2. IntegrityError 被捕获 → SSE error 帧 + end 帧。
  3. error 帧 code = E_ASSISTANT_CONCURRENT_MESSAGE。
  4. user msg seq = ai_session.message_count + 1（顺序写入正确性）。
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError as SAIntegrityError

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
    """AIMessage 属性的 fixture：用 PropertyMock 确保 message_count 返回真 int。"""
    s = MagicMock()
    # configure_mock 让默认访问返回 MagicMock，但 message_count 用 PropertyMock 固定值
    s.configure_mock(message_count=message_count)
    # 覆盖其他必需属性（避免 AttributeError）
    s.configure_mock(
        id=session_id,
        user_id=user_id,
        user_active=True,
        closed_at=None,
        persona_state_start="warm",
        persona_state_end="warm",
        total_llm_cost=Decimal("0"),
    )
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
    return event, json.loads("\n".join(data_lines))


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


def _mock_commit() -> AsyncMock:
    """session.commit mock：await 后返回 None，防止挂起。"""
    return AsyncMock(return_value=None)


# ---------------------------------------------------------------------------
# 1. SELECT 带 with_for_update（FOR UPDATE 行锁）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_message_stream_uses_select_for_update_lock() -> None:
    """验证 SELECT 语句携带 .with_for_update()，防止并发读出相同 message_count。"""
    user_id = "22222222-2222-4222-8222-222222222222"
    ai_session = _make_ai_session()
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = _mock_commit()

    await _collect_sse(
        send_message_stream(
            session,
            user_id=user_id,
            session_id="11111111-1111-4111-8111-111111111111",
            text="hello",
        )
    )

    assert session.execute.call_count >= 1
    first_call_args = session.execute.call_args_list[0]
    stmt = first_call_args[0][0]
    # SQLAlchemy select().with_for_update() 后内部属性 _for_update_arg 非 None
    assert hasattr(stmt, "_for_update_arg") and stmt._for_update_arg is not None, (
        "SELECT 语句必须携带 .with_for_update() 行锁，防止并发 seq 竞态"
    )


# ---------------------------------------------------------------------------
# 2. IntegrityError -> SSE error 帧（限流提示）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_message_stream_integrity_error_returns_rate_limit_sse() -> None:
    """IntegrityError → SSE error 帧，code=E_ASSISTANT_CONCURRENT_MESSAGE。"""
    user_id = "22222222-2222-4222-8222-222222222222"
    ai_session = _make_ai_session(message_count=5)
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()

    # FakeIntegrityError：直接继承避免 sqlalchemy 内部 __init__ 签名问题
    class FakeIntegrityError(SAIntegrityError):
        pass

    session.commit = AsyncMock(
        side_effect=FakeIntegrityError(
            "duplicate key",
            {"session_id": str(ai_session.id), "seq": 6},
            Exception("duplicate key value violates unique constraint"),
        )
    )

    frames = await _collect_sse(
        send_message_stream(
            session,
            user_id=user_id,
            session_id="11111111-1111-4111-8111-111111111111",
            text="hello",
        )
    )

    error_events = [(ev, d) for ev, d in frames if ev == "error"]
    assert len(error_events) == 1, f"期望 1 个 error 帧，实际: {frames}"
    _, data = error_events[0]
    assert data["code"] == "E_ASSISTANT_CONCURRENT_MESSAGE"
    assert "请求过于频繁" in data["message_zh"]

    end_events = [(ev, d) for ev, d in frames if ev == "end"]
    assert len(end_events) == 1
    assert end_events[0][1]["ok"] is False


# ---------------------------------------------------------------------------
# 3. seq 值等于 message_count + 1（顺序写入正确性）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_message_stream_user_msg_seq_equals_message_count_plus_one() -> None:
    """验证 user message 的 seq = ai_session.message_count + 1（正常路径）。"""
    user_id = "22222222-2222-4222-8222-222222222222"
    original_count = 3
    ai_session = _make_ai_session(message_count=original_count)
    session = AsyncMock()
    session.execute.return_value = _scalar_result(ai_session)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = _mock_commit()

    # patch _stream_chat：跳过 LLM 调用 + 后续 DB commit，直接 yield end 帧，
    # 避免测试依赖真实 LLM 或未 mock 的 session.get 等调用。
    async def mock_stream_chat(*args: Any, **kwargs: Any) -> Any:
        yield "event: end\ndata: {\"ok\":true,\"reply\":\"mocked\",\"persona_state\":\"warm\"}\n\n"

    with patch("app.services.assistant_service._stream_chat", mock_stream_chat):
        await _collect_sse(
            send_message_stream(
                session,
                user_id=user_id,
                session_id="11111111-1111-4111-8111-111111111111",
                text="test message",
            )
        )

    user_msg_adds = [
        c.args[0]
        for c in session.add.call_args_list
        if isinstance(c.args[0], AIMessage) and c.args[0].role == "user"
    ]
    assert len(user_msg_adds) == 1
    # seq 应该是原始 message_count + 1（代码：seq = ai_session.message_count + 1）
    assert user_msg_adds[0].seq == original_count + 1, (
        f"user msg seq 应为 {original_count + 1}，实际: {user_msg_adds[0].seq}"
    )
