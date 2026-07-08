"""M5 智能管家 service（4 态 FSM + SmartRouter A/B）。

真源：``docs/spec/SPEC-M5-persona-chat.md`` + ADR-0015。
- 4 态 FSM：warm / neutral / slight_hug / medical_guarded
- SmartRouter A：内容路由（fast / slow / medical_guarded / out_of_scope）
- SmartRouter B：状态切换触发器
- persona_state guard：medical_guarded 进入后所有回复都加 disclaimer
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import (
    audit_persona_state_switch,
    logger,
)
from app.db.models.ai_messages import AIMessage
from app.db.models.ai_sessions import AISession
from app.errors.codes import (
    E_ASSISTANT_FORBIDDEN_CALLER,
    E_ASSISTANT_LLM_ERROR,
    E_ASSISTANT_MESSAGE_INVALID,
    E_ASSISTANT_MESSAGE_TOO_LONG,
    E_ASSISTANT_SESSION_CLOSED,
    E_ASSISTANT_SESSION_NOT_FOUND,
)

# Persona 4 态
PERSONA_STATES: frozenset[str] = frozenset(
    {"warm", "neutral", "slight_hug", "medical_guarded"}
)
# 入口卡白名单（与 DDL db/init/03-checks.sql §3.10 chk_ai_session_entry 强一致）
ENTRY_CARDS: frozenset[str] = frozenset(
    {"smart_analyze", "mood_diary", "recall_self", "direct_input"}
)
# 入口卡兼容映射（旧值 → DDL 白名单），避免前端老数据 / 旧测试传非法值触发 500
ENTRY_CARD_COMPAT: dict[str, str] = {
    "checkin_done": "mood_diary",
    "report_result": "smart_analyze",
    "recall": "recall_self",
    "general": "direct_input",
}
# primary_intent 白名单（与 DDL chk_ai_session_intent 强一致）
PRIMARY_INTENTS: frozenset[str] = frozenset(
    {
        "module_redirect",
        "read_query",
        "recall",
        "recall_ack",
        "feedback_ack",
        "feedback_create",
        "medical_reject",
        "unknown",
    }
)
# primary_intent 兜底映射：非法值 / 旧枚举值 → "unknown"（最低风险）
PRIMARY_INTENT_COMPAT: dict[str, str] = {
    "general": "unknown",
    "direct_chat": "unknown",
    "chat": "unknown",
    "checkin": "unknown",
    "diagnosis": "module_redirect",
}
DEFAULT_PRIMARY_INTENT = "unknown"
MAX_MESSAGE_LENGTH = 1000
DEFAULT_STATE = "warm"
# 触发 medical_guarded 的医疗关键词（最小集 + 复用 medical-reject-words）
MEDICAL_TRIGGERS: tuple[str, ...] = (
    "治疗",
    "治愈",
    "病",
    "处方",
    "医生",
    "医院",
    "打针",
    "玻尿酸",
    "瘦脸针",
    "微整",
    "整形",
)


class AssistantError(SelfwellError):
    """智能管家业务异常。"""

    code: str = E_ASSISTANT_MESSAGE_INVALID
    message_zh: str = "智能管家请求无效"
    message_en: str = "Invalid assistant request"
    severity = "USER_ERROR"
    http_status = 400


class SessionNotFoundError(AssistantError):
    code: str = E_ASSISTANT_SESSION_NOT_FOUND
    message_zh: str = "会话不存在"
    message_en: str = "Session not found"
    http_status = 404


class SessionClosedError(AssistantError):
    code: str = E_ASSISTANT_SESSION_CLOSED
    message_zh: str = "会话已关闭"
    message_en: str = "Session closed"
    http_status = 410


class LLMUnavailableError(AssistantError):
    code: str = E_ASSISTANT_LLM_ERROR
    message_zh: str = "AI 服务暂不可用"
    message_en: str = "AI service unavailable"
    http_status = 503
    severity = "TRANSIENT"


def _classify_intent(text: str) -> str:
    """SmartRouter A：内容路由。"""
    if any(kw in text for kw in MEDICAL_TRIGGERS):
        return "medical_guarded"
    if any(kw in text for kw in ("几点", "什么时候", "多久", "几天", "怎么样", "为何")):
        return "slow"
    return "fast"


def _next_state(current: str, intent: str) -> str:
    """SmartRouter B：状态切换。"""
    if intent == "medical_guarded":
        return "medical_guarded"
    if current == "medical_guarded":
        return "medical_guarded"  # medical_guarded 是吸收态
    # warm → neutral → slight_hug 随交互轮次自然升级
    if current == "warm" and intent == "fast":
        return "neutral"
    if current == "neutral" and intent == "slow":
        return "slight_hug"
    return current


def _render_by_state(state: str, intent: str) -> str:
    """按 state 渲染回复。"""
    base = {
        "warm": "今天感觉怎么样？我在这里陪着你。",
        "neutral": "嗯嗯，继续保持这个节奏。",
        "slight_hug": "你已经走了这么远，给自己一个拥抱。",
        "medical_guarded": "我无法回答医疗问题，建议您咨询专业医师。",
    }
    reply = base.get(state, base["warm"])
    if state == "medical_guarded":
        return reply
    if intent == "slow":
        reply += "（这条需要多想想，AI 在认真回应你）"
    return reply


def _normalize_entry_card(entry_card: str | None) -> tuple[str | None, bool]:
    """入口卡白名单校验 + 旧值兼容映射。

    Returns:
        (normalized_value, was_compat_mapped)

    """
    if entry_card is None:
        return None, False
    if entry_card in ENTRY_CARDS:
        return entry_card, False
    mapped = ENTRY_CARD_COMPAT.get(entry_card)
    if mapped is not None and mapped in ENTRY_CARDS:
        return mapped, True
    raise AssistantError(
        f"entry_card 非法：{entry_card}",
        code=E_ASSISTANT_FORBIDDEN_CALLER,
        field="entry_card",
    )


def _normalize_primary_intent(primary_intent: str) -> tuple[str, bool]:
    """primary_intent 白名单校验 + 旧值兼容映射。

    Returns:
        (normalized_value, was_compat_mapped)

    """
    if primary_intent in PRIMARY_INTENTS:
        return primary_intent, False
    mapped = PRIMARY_INTENT_COMPAT.get(primary_intent)
    if mapped is not None and mapped in PRIMARY_INTENTS:
        return mapped, True
    # 兜底：未知值统一落到 unknown，避免 500
    return DEFAULT_PRIMARY_INTENT, True


async def create_session(
    session: AsyncSession,
    *,
    user_id: str,
    entry_card: str | None = None,
    primary_intent: str = DEFAULT_PRIMARY_INTENT,
) -> dict[str, Any]:
    """创建会话。"""
    ec, ec_mapped = _normalize_entry_card(entry_card)
    pi, pi_mapped = _normalize_primary_intent(primary_intent)
    if ec_mapped:
        logger.warning(
            "assistant_entry_card_compat_mapped",
            original=entry_card,
            normalized=ec,
            user_id=user_id,
        )
    if pi_mapped:
        logger.warning(
            "assistant_primary_intent_compat_mapped",
            original=primary_intent,
            normalized=pi,
            user_id=user_id,
        )
    now_ts = datetime.now(UTC)
    ai_session = AISession(
        id=uuid4(),
        user_id=user_id,
        entry_card=ec,
        primary_intent=pi,
        persona_state_start=DEFAULT_STATE,
        persona_state_end=DEFAULT_STATE,
        message_count=0,
        total_llm_cost=Decimal("0.0000"),
        user_active=True,
        started_at=now_ts,
        last_active_at=now_ts,
        created_at=now_ts,
        created_by=str(user_id),         # 当前创建用户（会话发起人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),    # 当前更新用户
    )
    session.add(ai_session)
    await session.flush()
    logger.info("assistant_session_created", session_id=str(ai_session.id), user_id=user_id)
    return {
        "session_id": str(ai_session.id),
        "persona_state": ai_session.persona_state_start,
        "entry_card": ec,
    }


async def send_message(
    session: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    text: str,
) -> dict[str, Any]:
    """发送用户消息 + AI 回复。"""
    if not text or len(text) > MAX_MESSAGE_LENGTH:
        raise UserInputError(
            f"消息长度超限（{len(text) if text else 0} > {MAX_MESSAGE_LENGTH}）",
            code=E_ASSISTANT_MESSAGE_TOO_LONG,
            field="text",
            limit=MAX_MESSAGE_LENGTH,
        )

    # 1. 加载 session
    stmt = select(AISession).where(
        AISession.id == session_id, AISession.user_id == user_id
    )
    result = await session.execute(stmt)
    ai_session = result.scalar_one_or_none()
    if ai_session is None:
        raise SessionNotFoundError(field="session_id")
    if not ai_session.user_active or ai_session.closed_at is not None:
        raise SessionClosedError(field="session_id")

    # 2. 写 user message
    now_ts = datetime.now(UTC)
    seq = ai_session.message_count + 1
    user_msg = AIMessage(
        id=uuid4(),
        session_id=ai_session.id,
        seq=seq,
        role="user",
        content=text,
        referenced_feedback_ids=[],
        referenced_video_ids=[],
        token_count=len(text),
        created_at=now_ts,
        created_by=str(user_id),         # 当前创建用户（发消息的人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),    # 当前更新用户
    )
    session.add(user_msg)
    ai_session.message_count = seq
    ai_session.last_active_at = now_ts

    # 3. SmartRouter A（intent）
    intent = _classify_intent(text)
    from_state = ai_session.persona_state_end or ai_session.persona_state_start
    to_state = _next_state(from_state, intent)

    # 4. persona_state 切换 + 审计
    if to_state != from_state:
        ai_session.persona_state_end = to_state
        audit_persona_state_switch(
            user_id_pseudo=str(user_id)[:8],
            from_state=from_state,
            to_state=to_state,
            trigger=intent,
            session_id=session_id,
        )

    # 5. AI 回复：文本 LLM 主备链 + 静态文案兜底
    from app.llm.client import LLMMessage, TextRequest
    from app.llm.text_chain import TextFallbackChain

    fallback_reply = _render_by_state(to_state, intent)
    reply_text = fallback_reply
    llm_model = "static-fallback"
    llm_cost = Decimal("0.0000")
    if to_state != "medical_guarded":
        request = TextRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "你是 Selfwell 智能管家，只提供陪伴、习惯建议和基础调理常识。"
                        "不得给出诊断、处方、注射、医美治疗或疗效承诺。"
                    ),
                ),
                LLMMessage(role="user", content=text),
            ],
            metadata={"persona_state": to_state, "intent": intent, "session_id": session_id},
        )
        chain = TextFallbackChain(on_all_failed=lambda _request: fallback_reply)
        try:
            llm_result = await chain.run(request)
            reply_text = llm_result.content.strip() or fallback_reply
            llm_model = llm_result.provider_used
            llm_cost = Decimal(str(llm_result.cost_yuan))
        except Exception as exc:
            logger.warning(
                "assistant_text_chain_fallback",
                error_type=type(exc).__name__,
                error_message=str(exc)[:200],
            )
    safety_passed = to_state != "medical_guarded"

    seq2 = ai_session.message_count + 1
    assistant_msg = AIMessage(
        id=uuid4(),
        session_id=ai_session.id,
        seq=seq2,
        role="assistant",
        content=reply_text,
        safety_passed=safety_passed,
        llm_model=llm_model,
        llm_latency_ms=120,
        llm_cost=llm_cost,
        referenced_feedback_ids=[],
        referenced_video_ids=[],
        token_count=len(reply_text),
        created_at=now_ts,
        created_by=str(user_id),         # AI 消息由用户对话触发，记用户
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),    # 当前更新用户
    )
    session.add(assistant_msg)
    ai_session.message_count = seq2
    ai_session.total_llm_cost = (ai_session.total_llm_cost or Decimal("0")) + llm_cost

    await session.flush()
    return {
        "session_id": session_id,
        "user_message_id": str(user_msg.id),
        "assistant_message_id": str(assistant_msg.id),
        "reply": reply_text,
        "persona_state": to_state,
        "intent": intent,
        "safety_passed": safety_passed,
    }


async def close_session(
    session: AsyncSession, *, user_id: str, session_id: str
) -> dict[str, Any]:
    """关闭会话。"""
    stmt = select(AISession).where(
        AISession.id == session_id, AISession.user_id == user_id
    )
    result = await session.execute(stmt)
    ai_session = result.scalar_one_or_none()
    if ai_session is None:
        raise SessionNotFoundError(field="session_id")
    now_ts = datetime.now(UTC)
    ai_session.closed_at = now_ts
    ai_session.user_active = False
    ai_session.last_updated_time = now_ts
    await session.flush()
    return {"session_id": session_id, "closed_at": now_ts.isoformat()}


async def list_messages(
    session: AsyncSession, *, user_id: str, session_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    """列出消息历史。"""
    stmt = (
        select(AIMessage)
        .where(AIMessage.session_id == session_id)
        .order_by(AIMessage.seq.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        {
            "message_id": str(m.id),
            "seq": m.seq,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in result.scalars().all()
    ]


__all__ = [
    "DEFAULT_PRIMARY_INTENT",
    "DEFAULT_STATE",
    "ENTRY_CARDS",
    "ENTRY_CARD_COMPAT",
    "MAX_MESSAGE_LENGTH",
    "PERSONA_STATES",
    "PRIMARY_INTENTS",
    "PRIMARY_INTENT_COMPAT",
    "AssistantError",
    "LLMUnavailableError",
    "SessionClosedError",
    "SessionNotFoundError",
    "_normalize_entry_card",
    "_normalize_primary_intent",
    "close_session",
    "create_session",
    "list_messages",
    "send_message",
]
