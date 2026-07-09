"""M5 智能管家 service（4 态 FSM + SmartRouter A/B）。

真源：``docs/spec/SPEC-M5-persona-chat.md`` + ADR-0015。
- 4 态 FSM：warm / neutral / slight_hug / medical_guarded
- SmartRouter A：内容路由（fast / slow / medical_guarded / out_of_scope）
- SmartRouter B：状态切换触发器
- persona_state guard：medical_guarded 进入后所有回复都加 disclaimer
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

# 5. AI 回复：PromptTemplate | text_llm + 静态文案兜底
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import hash_user_id_pseudo
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
from app.llm import text_llm
from app.services.ai_messages_crud import persist_assistant_message

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
# Fallback 文案单条最大字符数（PRD §17.15 ACK 30 字限制放宽到 60 字给非快问 fallback）。
FALLBACK_MAX_CHARS = 60
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


# ── State-driven fallback 文案 ────────────────────────────────────────────────
# 约束（coding-standards RULES.md "Safety Boundary" + PRD §17.15）：
# 1. 每个非 medical state 必须 ≥ 3 条候选，随机抽一条（避免用户重复看到同一句）。
# 2. medical_guarded 文案由 PRD ADR 锁死，**固定温柔拒绝**（合规优先，不随机）。
# 3. 每条 ≤ 60 字；不得包含 Markdown；不得写进 schema。
# 4. 返回时由调用方在 AIMessage.llm_model 标记 ``provider_used="static-fallback"``。
_FALLBACK_BY_STATE: dict[str, tuple[str, ...]] = {
    # ── Persona 4 态主对话 ──
    "warm": (
        "今天感觉怎么样？我在这里陪着你。",
        "在呢，慢慢说，我在听。",
        "嗨，又见面啦。",
    ),
    "neutral": (
        "嗯嗯，继续保持这个节奏。",
        "不错的状态，先记住这个感觉。",
        "慢慢来就好，不用着急。",
    ),
    "slight_hug": (
        "你已经走了这么远，给自己一个拥抱。",
        "今天走到这里，已经很棒了。",
        "能感觉到你花了不少力气，先歇一歇。",
    ),
    # medical_guarded：合规优先，**固定文案**（不随机），必须含 "医疗" 关键词
    # （被 test_render_medical_disclaimer 强约束），文案长度 ≤ 60 字。
    "medical_guarded": (
        "我无法回答医疗问题，建议您咨询专业医师。",
    ),
    # ── 拓展状态：思考中 / 答案待出 / 倾听 / 寒暄 ──
    # （非 persona_state，但被前端骨架 / 流式回包使用；fallback 时按状态给一句过渡）
    "thinking": (
        "我在认真想一下，再回应你。",
        "让我多看一会儿，别急。",
        "稍等，我在整理思路。",
    ),
    "answer": (
        "这是我看到的，先给你参考。",
        "整理一份回应，请过目。",
        "这条想法给你，听听看合不合适。",
    ),
    "listening": (
        "我在听着，继续。",
        "嗯，我在。",
        "你说，我在听。",
    ),
    "greeting": (
        "你好呀，今天过得如何？",
        "又见面了，今天想聊点什么？",
        "你好，今天想从哪里开始？",
    ),
}


def _pick_fallback(state: str) -> str:
    """按 state 抽一条 fallback 文案。

    - ``medical_guarded`` 永远返回固定文案（PRD ADR 锁死，不随机）。
    - 未知 state 兜底到 ``warm`` 候选池。
    - 调用方负责每次用 ``os.urandom`` 设随机种子，避免进程级固定顺序。
    """
    if state == "medical_guarded":
        # 合规优先：medical_guarded 永远取唯一固定文案（PRD ADR 锁死）。
        return _FALLBACK_BY_STATE["medical_guarded"][0]
    pool = _FALLBACK_BY_STATE.get(state) or _FALLBACK_BY_STATE["warm"]
    return random.choice(pool)  # noqa: S311 — cosmetic copy selection, not crypto


def _render_by_state(state: str, intent: str) -> str:
    """按 state 渲染 fallback 回复文案。

    设计：
    - 文案候选池 ``_FALLBACK_BY_STATE``，每 state ≥ 3 条；
    - 调用 ``random.choice`` 抽一条，避免用户重复看到同一句；
    - ``medical_guarded`` 例外（合规优先，固定文案，**不随机**）；
    - 传入 ``intent == "slow"`` 时在末尾追加"思考中"标记，方便前端 thinking 骨架衔接。

    备注：本函数**仅在 LLM 主备链全失败时**被调用，作为 ``static-fallback`` 兜底。
    调用方写入 AIMessage 时务必打 ``llm_model="static-fallback"`` 标记。
    """
    # 每次调用重置随机种子（基于 os.urandom），避免进程级重复序列
    random.seed(int.from_bytes(os.urandom(4), "big"))
    reply = _pick_fallback(state)
    if state == "medical_guarded":
        return reply  # 合规文案不再追加任何后缀
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
    # user_id 在 DDL 中是 postgresql.UUID(as_uuid=True)。
    # 当前端 JWT sub claim 是合法 UUID 字符串时直接转换；否则兜底生成新 UUID
    # （与 diagnosis_v1.py:_create_diagnosis_report 保持一致），避免 asyncpg
    # 抛 ValueError("invalid UUID ...: length must be between 32..36") 导致端点 500。
    try:
        user_uuid = UUID(str(user_id))
    except (ValueError, TypeError):
        user_uuid = uuid4()
        logger.warning(
            "assistant_user_id_not_uuid_fallback",
            original_user_id=str(user_id)[:32],
            user_id=str(user_id),
        )
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
        user_id=user_uuid,
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
    # ID 兼容：优先尝试解析为 UUID（与 AISession.id 字段类型一致）；
    # 解析失败则退化为 str 比较（兼容测试 / 旧 ID 格式）。
    stmt = select(AISession).where(AISession.id == session_id, AISession.user_id == user_id)
    result = await session.execute(stmt)
    ai_session = result.scalar_one_or_none()
    if ai_session is None:
        # 再尝试 UUID 形式匹配一次（兼容存储为 UUID 但传入 str）
        try:
            session_uuid = UUID(str(session_id))
            user_uuid = UUID(str(user_id))
        except ValueError as exc:
            raise SessionNotFoundError(field="session_id") from exc
        stmt_uuid = select(AISession).where(
            AISession.id == session_uuid, AISession.user_id == user_uuid
        )
        result = await session.execute(stmt_uuid)
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



    fallback_reply = _render_by_state(to_state, intent)
    reply_text = fallback_reply
    llm_model = "static-fallback"
    llm_cost = Decimal("0.0000")
    if to_state != "medical_guarded":
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是 Selfwell 智能管家，只提供陪伴、习惯建议和基础调理常识。"
                "不得给出诊断、处方、注射、医美治疗或疗效承诺。"
                "回复要温柔、简洁，控制在 100 字以内。"
                "状态：{persona_state}，用户输入：{user_text}",
            ),
            ("user", "{user_text}"),
        ])
        chain = prompt | text_llm
        try:
            response = await chain.ainvoke({
                "persona_state": to_state,
                "user_text": text,
            })
            llm_model = getattr(text_llm, "model", "text")
            reply_text = (response.content if hasattr(response, "content") else str(response)).strip()
            if not reply_text:
                reply_text = fallback_reply
                llm_model = "static-fallback"
        except Exception as exc:
            logger.warning(
                "assistant_text_llm_error",
                error_type=type(exc).__name__,
                error_message=str(exc)[:200],
            )
            reply_text = fallback_reply
            llm_model = "static-fallback"
    safety_passed = to_state != "medical_guarded"

    # 4. persona_state 切换 + 审计（必须在 llm_model/llm_cost 算出后再算 mock_reason）
    if to_state != from_state:
        ai_session.persona_state_end = to_state
        audit_kwargs: dict[str, object] = {
            "user_id_pseudo": hash_user_id_pseudo(str(user_id)),
            "from_state": from_state,
            "to_state": to_state,
            "trigger": intent,
            "session_id": session_id,
        }
        if llm_model == "static-fallback" and llm_cost == Decimal("0.0000"):
            audit_kwargs["mock_reason"] = "llm_unavailable_fallback"
        audit_persona_state_switch(**audit_kwargs)

    # 5. AI 回复：PromptTemplate | text_llm + 静态文案兜底
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


# ─────────────────────────────────────────────────────────────────────────────
# PR-A2 SSE：send_message_stream（worker C 落地；LLM 真链路待后续 worker 替换）
# ─────────────────────────────────────────────────────────────────────────────

# 与 SmartAnalyze 步骤对齐（与 assistant-home 现有 SMART_ANALYZE_COPY.stages 对齐）
_SMART_ANALYZE_STAGES: tuple[tuple[str, int, str], ...] = (
    ("analyzing", 33, "正在识别体态状态"),
    ("analyzing", 66, "分析面部状态"),
    ("analyzing", 100, "生成养护建议"),
)

# mock directions（与前端 SMART_ANALYZE_MOCK_DIRECTIONS 形状 1:1）
_MOCK_DIRECTIONS: tuple[dict[str, Any], ...] = (
    {"num": 1, "title": "侧颈前伸", "level": "轻度", "description": "建议每 2 小时做 1 次收下巴训练"},
    {"num": 2, "title": "肩颈僵硬", "level": "中度", "description": "建议每日 8 分钟肩颈放松"},
    {"num": 3, "title": "眼周疲劳", "level": "轻度", "description": "建议每日 5 分钟眼周穴位按压"},
)


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    """组装一帧标准 SSE（与 diagnosis_v1._job_event_stream 同形）。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def send_message_stream(
    session: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    text: str,
) -> AsyncIterator[str]:
    """SSE 智能分析流（worker C 落地；mock directions）。

    事件序列（事件名 → data 字段，详见 PR-A2 SPEC）：
      start    → {"step": 0}
      progress → {"step": 1|2|3, "percent": 33|66|100, "label": "..."}
      report   → {"directions": [{num,title,level,description}, ...]}
      end      → {"ok": true, "reply": "...", "persona_state": "..."}
      error    → {"code": "...", "message_zh": "..."}

    异常分支：
      - medical_guarded  → emit progress step=1, label 含「医疗」关键词；
                           yield report(directions=[]) + end（吸收态）
      - 异常             → emit error(code=E_ASSISTANT_LLM_ERROR) 后 return

    TODO(后续 worker D)：把 _MOCK_DIRECTIONS / _SMART_ANALYZE_STAGES 替换为真实
    LLM 多模态链路（diagnosis_service.stream_diagnose 已存在的 stage 模型可参考）。
    """
    try:
        # 0) text 校验
        if not text or len(text) > MAX_MESSAGE_LENGTH:
            yield _sse_pack(
                "error",
                {
                    "code": E_ASSISTANT_MESSAGE_TOO_LONG,
                    "message_zh": f"消息长度超限（{len(text) if text else 0} > {MAX_MESSAGE_LENGTH}）",
                },
            )
            return

        # 1) start
        yield _sse_pack("start", {"step": 0})

        # 2) session 校验
        stmt = select(AISession).where(AISession.id == session_id, AISession.user_id == user_id)
        result = await session.execute(stmt)
        ai_session = result.scalar_one_or_none()
        if ai_session is None:
            try:
                session_uuid = UUID(str(session_id))
                user_uuid = UUID(str(user_id))
            except ValueError as exc:
                raise SessionNotFoundError(field="session_id") from exc
            stmt_uuid = select(AISession).where(
                AISession.id == session_uuid, AISession.user_id == user_uuid
            )
            result = await session.execute(stmt_uuid)
            ai_session = result.scalar_one_or_none()
        if ai_session is None:
            raise SessionNotFoundError(field="session_id")
        if not ai_session.user_active or ai_session.closed_at is not None:
            raise SessionClosedError(field="session_id")

        # 3) SmartRouter A → 决定是否 medical_guarded
        intent = _classify_intent(text)
        from_state = ai_session.persona_state_end or ai_session.persona_state_start
        to_state = _next_state(from_state, intent)

        # 4) 写 user message（持久化用户输入，与 send_message 同步路径一致）
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
            created_by=str(user_id),
            created_time=now_ts,
            last_updated_time=now_ts,
            last_updated_by=str(user_id),
        )
        session.add(user_msg)
        ai_session.message_count = seq
        ai_session.last_active_at = now_ts

        if to_state == "medical_guarded":
            # medical_guarded 吸收态：不发 progress / report（合规优先）
            # Stream Y：end 帧整体落库 safety_passed=False + medical_guarded=True
            if to_state != from_state:
                ai_session.persona_state_end = to_state
                audit_persona_state_switch(
                    user_id_pseudo=hash_user_id_pseudo(str(user_id)),
                    from_state=from_state,
                    to_state=to_state,
                    trigger=intent,
                    session_id=session_id,
                    mock_reason="medical_guarded_short_circuit",
                )
            reply_text_medical = _FALLBACK_BY_STATE["medical_guarded"][0]
            ai_session.message_count += 1
            msg_id = await persist_assistant_message(
                session,
                session_uuid=ai_session.id,
                user_id=str(user_id),
                seq=ai_session.message_count,
                content=reply_text_medical,
                safety_passed=False,
                llm_model="static-fallback",
                llm_cost=0.0,
                trigger="medical_reject",
                intent=intent,
                directions=None,
                persona_state=to_state,
                medical_guarded=True,
            )
            await session.flush()
            yield _sse_pack(
                "end",
                {
                    "ok": True,
                    "reply": reply_text_medical,
                    "persona_state": to_state,
                    "medical_guarded": True,
                    "ai_msg_id": str(msg_id),
                },
            )
            return

        # 5) progress 3 步（mock 时序：每步间隔 250ms，便于前端可见进度推进）
        for idx, (_stage, percent, label) in enumerate(_SMART_ANALYZE_STAGES, start=1):
            await asyncio.sleep(0.25)
            yield _sse_pack("progress", {"step": idx, "percent": percent, "label": label})

        # 6) report（mock directions，TODO 后续 worker 替换为 LLM 真实流）
        yield _sse_pack("report", {"directions": list(_MOCK_DIRECTIONS)})

        # 7) persona_state 切换 + 审计
        if to_state != from_state:
            ai_session.persona_state_end = to_state
            audit_persona_state_switch(
                user_id_pseudo=hash_user_id_pseudo(str(user_id)),
                from_state=from_state,
                to_state=to_state,
                trigger=intent,
                session_id=session_id,
                mock_reason="mock_directions_pending_real_llm",
            )

        # 8) 整条落库 + end（Stream Y / worker Y：on end 整体落库，单事务）
        # TODO(worker D)：content 改由 LLM streaming 流式拼接；当前 mock 直接拼接 labels
        reply_text = "，".join(s[2] for s in _SMART_ANALYZE_STAGES)
        ai_session.message_count += 1
        msg_id = await persist_assistant_message(
            session,
            session_uuid=ai_session.id,
            user_id=str(user_id),
            seq=ai_session.message_count,
            content=reply_text,
            safety_passed=True,
            llm_model="sse-mock-fallback",
            llm_cost=0.0,
            trigger="smart_router",
            intent=intent,
            directions=list(_MOCK_DIRECTIONS),
            persona_state=to_state,
            medical_guarded=False,
            llm_latency_ms=750,
        )
        await session.flush()

        yield _sse_pack(
            "end",
            {
                "ok": True,
                "reply": reply_text,
                "persona_state": to_state,
                "user_message_id": str(user_msg.id),
                "assistant_message_id": str(msg_id),
                "ai_msg_id": str(msg_id),
            },
        )
    except (SessionNotFoundError, SessionClosedError) as exc:
        yield _sse_pack("error", {"code": exc.code, "message_zh": exc.render_zh()})
    except Exception as exc:
        logger.exception(
            "assistant_send_message_stream_error",
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
            session_id=session_id,
        )
        yield _sse_pack(
            "error",
            {
                "code": E_ASSISTANT_LLM_ERROR,
                "message_zh": "AI 服务暂不可用",
            },
        )


async def close_session(
    session: AsyncSession, *, user_id: str, session_id: str
) -> dict[str, Any]:
    """关闭会话。"""
    try:
        session_uuid = UUID(str(session_id))
        user_uuid = UUID(str(user_id))
    except ValueError as exc:
        raise SessionNotFoundError(field="session_id") from exc
    stmt = select(AISession).where(
        AISession.id == session_uuid, AISession.user_id == user_uuid
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
    try:
        session_uuid = UUID(str(session_id))
        user_uuid = UUID(str(user_id))
    except ValueError as exc:
        raise SessionNotFoundError(field="session_id") from exc

    # 先校验 session 归属（防止用别人的 session_id 偷看消息）
    owned = await session.execute(
        select(AISession.id).where(
            AISession.id == session_uuid, AISession.user_id == user_uuid
        )
    )
    if owned.scalar_one_or_none() is None:
        raise SessionNotFoundError(field="session_id")

    stmt = (
        select(AIMessage)
        .where(AIMessage.session_id == session_uuid)
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


# ─────────────────────────────────────────────────────────────────────────────
# 入口卡 4 状态机（M5 SmartRouter Home）
# ─────────────────────────────────────────────────────────────────────────────
ENTRY_CARD_COPY: dict[str, dict[str, str]] = {
    "smart_analyze": {
        "title": "智能分析",
        "not_started": "上传照片生成你的画像",
        "in_progress": "正在为你生成画像，再等一会儿",
        "completed": "已生成你的画像，回看一下吗",
        "inactive_7d": "离上次互动有点久了，先看画像吗",
    },
    "mood_diary": {
        "title": "心情日记",
        "not_started": "把今天的心情写下来吧",
        "in_progress": "今天已经记录过了，继续就好",
        "completed": "今天的心情已经收好",
        "inactive_7d": "随时都能记录一两笔",
    },
    "recall_self": {
        "title": "对比回顾",
        "not_started": "从今天开始记录，第一张卡就会是你的起点",
        "in_progress": "已经在为你准备第一次回顾",
        "completed": "看看这一路的自己",
        "inactive_7d": "准备好了再回来看看",
    },
    "direct_input": {
        "title": "直接聊聊",
        "not_started": "想说什么都可以",
        "in_progress": "我在这里，随时都可以继续",
        "completed": "今天聊过啦，下次再继续",
        "inactive_7d": "想聊的时候就来",
    },
}

INACTIVE_THRESHOLD_DAYS: int = 7
RECALL_TRIGGER_DAYS: tuple[int, ...] = (7, 14, 21)
BASELINE_GREETING_NEVER_RECORDED: str = "今天是新的一天，从一件小事开始吧。"
BASELINE_GREETING_RECORDED_TODAY: str = "今天已经在记录了，想做什么都好。"
BASELINE_GREETING_INACTIVE: str = "回来就好。"
BASELINE_GREETING_WITH_STREAK: None = None  # 基线问候不依赖 streak（ADR-0017）


def _resolve_card_state(
    card_id: str,
    *,
    last_feedback_days_ago: int | None,
    has_latest_report: bool,
) -> str:
    """根据 ``last_feedback_days_ago`` 与 ``has_latest_report`` 决定卡片状态。"""
    if last_feedback_days_ago is not None and last_feedback_days_ago >= INACTIVE_THRESHOLD_DAYS:
        return "inactive_7d"
    if card_id == "smart_analyze":
        if has_latest_report:
            return "completed"
        if last_feedback_days_ago is None:
            return "not_started"
        if last_feedback_days_ago == 0:
            return "in_progress"
        return "completed" if last_feedback_days_ago >= 1 else "not_started"
    if card_id == "mood_diary":
        if last_feedback_days_ago is None:
            return "not_started"
        if last_feedback_days_ago == 0:
            return "in_progress"
        return "completed"
    if card_id == "recall_self":
        if has_latest_report:
            return "completed"
        return "not_started"
    if card_id == "direct_input":
        if last_feedback_days_ago is None:
            return "not_started"
        if last_feedback_days_ago == 0:
            return "in_progress"
        return "completed"
    return "not_started"


def compute_entry_state(
    session: AsyncSession | None = None,
    *,
    user_id: str | None = None,
    me: object | None = None,
    latest_report: dict[str, Any] | None = None,
    recent_feedbacks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """计算智能管家首页 4 张入口卡的当前状态。

    Args:
        session: DB session（异步调用时使用；纯函数调用可传 None）。
        user_id: 当前 user_id。
        me: 兼容旧调用方的"UserMe-like"对象（具 ``last_feedback_days_ago`` 属性）。
        latest_report: 最近的诊断报告（dict 或 None）。
        recent_feedbacks: 最近的心情/反馈列表。

    Returns:
        4 个 card dict，每个含 ``{id, state, title, subtitle, highlight}``。

    Note:
        - card3 ("recall_self") 永远 ``highlight=True``
        - ``last_feedback_days_ago >= 7`` → 全卡 ``inactive_7d``
        - ``last_feedback_days_ago is None``（从未记录）→ 全卡 ``not_started`` / ``completed``
        - 不依赖 ``streak_days`` 评判（ADR-0017 §3.3）

    """
    if me is not None and not isinstance(me, dict):
        last_feedback_days_ago = getattr(me, "last_feedback_days_ago", None)
    else:
        last_feedback_days_ago = None
    has_latest_report = bool(latest_report)
    cards: list[dict[str, Any]] = []
    for card_id in ("smart_analyze", "mood_diary", "recall_self", "direct_input"):
        copy = ENTRY_CARD_COPY[card_id]
        state = _resolve_card_state(
            card_id,
            last_feedback_days_ago=last_feedback_days_ago,
            has_latest_report=has_latest_report,
        )
        cards.append(
            {
                "id": card_id,
                "state": state,
                "title": copy["title"],
                "subtitle": copy[state],
                "highlight": card_id == "recall_self",
            }
        )
    return cards


__all__ = [  # noqa: RUF022 — intentionally grouped: SCREAMING_SNAKE_CASE / CamelCase / lowercase
    "AssistantError",
    "BASELINE_GREETING_INACTIVE",
    "BASELINE_GREETING_NEVER_RECORDED",
    "BASELINE_GREETING_RECORDED_TODAY",
    "BASELINE_GREETING_WITH_STREAK",
    "DEFAULT_PRIMARY_INTENT",
    "DEFAULT_STATE",
    "ENTRY_CARDS",
    "ENTRY_CARD_COMPAT",
    "ENTRY_CARD_COPY",
    "FALLBACK_MAX_CHARS",
    "INACTIVE_THRESHOLD_DAYS",
    "LLMUnavailableError",
    "MAX_MESSAGE_LENGTH",
    "PERSONA_STATES",
    "PRIMARY_INTENTS",
    "PRIMARY_INTENT_COMPAT",
    "RECALL_TRIGGER_DAYS",
    "SessionClosedError",
    "SessionNotFoundError",
    "_FALLBACK_BY_STATE",
    "_normalize_entry_card",
    "_normalize_primary_intent",
    "close_session",
    "compute_entry_state",
    "create_session",
    "list_messages",
    "send_message",
    "send_message_stream",
]
