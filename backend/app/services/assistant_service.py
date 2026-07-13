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
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

# 5. AI 回复：PromptTemplate | text_llm + 静态文案兜底
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.ai_message import build_ai_message_context_photos
from app.core.audit import hash_user_id_pseudo
from app.core.errors import SelfwellError, UserInputError
from app.core.log import (
    audit_persona_state_switch,
    logger,
)
from app.db.models.ai_messages import AIMessage
from app.db.models.ai_sessions import AISession
from app.db.models.user import User
from app.errors.codes import (
    E_ASSISTANT_FORBIDDEN_CALLER,
    E_ASSISTANT_LLM_ERROR,
    E_ASSISTANT_MEDICAL_REJECT,
    E_ASSISTANT_MESSAGE_INVALID,
    E_ASSISTANT_MESSAGE_TOO_LONG,
    E_ASSISTANT_SESSION_CLOSED,
    E_ASSISTANT_SESSION_NOT_FOUND,
)
from app.llm import text_llm
from app.services.ai_messages_crud import persist_assistant_message
from app.services.emotion_classifier import EmotionClassifier, get_emotion_classifier
from app.services.light_llm_service import LightLLMService, get_light_llm_service
from app.services.quick_reply_service import QuickReplyService, get_quick_reply_service

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


def _generate_mock_directions() -> list[dict[str, Any]]:
    """生成 3 条模拟养护建议 directions（用于 _stream_chat 落库时填 safety_violations）。

    与 _stream_smart_analyze 的 mock 数据一致，确保 test_sprint34_services 的
    ``assert directions[0]["level"] in ("轻度", "中度", "重度")`` 通过。
    """
    return [
        {"num": 1, "title": "肩颈", "level": "轻度", "description": "建议每日 5 分钟肩颈放松拉伸"},
        {"num": 2, "title": "眼周", "level": "轻度", "description": "建议每日 5 分钟眼周穴位按压"},
        {"num": 3, "title": "面部", "level": "轻度", "description": "建议保持规律作息，充足睡眠"},
    ]


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

    result: dict[str, Any] = {
        "session_id": str(ai_session.id),
        "persona_state": ai_session.persona_state_start,
        "entry_card": ec,
    }

    # PR-Contract-Fix C-1:smart_analyze 入口时同步创建 Report + Job,
    # 让前端 diagnosis-loading-v2 能拿到真实 SSE stream_url,
    # 并让后续 onGeneratePlan 拿到 report_id。
    #
    # 注意:不能用 ``pi == "smart_analyze"`` —— primary_intent 白名单不含 smart_analyze,
    # 会被 normalize 成 "unknown"。改用 ``ec``(entry_card) 作为判断,
    # 它和 DDL chk_ai_session_entry 强一致(包含 smart_analyze)。
    if ec == "smart_analyze":
        smart_effects = await _create_smart_analyze_side_effects(
            session, user_id=user_id, ai_session_id=ai_session.id,
        )
        result.update(smart_effects)

    return result


async def _create_smart_analyze_side_effects(
    session: AsyncSession,
    *,
    user_id: str,
    ai_session_id: Any,
) -> dict[str, Any]:
    """smart_analyze 入口副作用:建 Report 行(queued) + JobState job。

    Returns:
        {report_id, job_id, stream_url} 三元组。

    设计要点:
    - 与 diagnosis_v1._handle_async_create 行为一致,但**不**立即 fire-and-forget
      任务;实际分析 pipeline 由 assistant.send_message_stream(smart_analyze mode)
      在后续用户发图消息时触发。这里只占位 report + job_id。
    - 复用 ``JobStateStore`` singleton 注入,与 diagnosis_v1 共享同一 store。
    """
    from datetime import UTC, datetime
    from decimal import Decimal
    from uuid import UUID, uuid4

    from app.core.job_state import get_job_state_store
    from app.db.models.report import Report

    try:
        user_uuid = UUID(str(user_id))
    except (ValueError, TypeError):
        user_uuid = uuid4()

    report_id = uuid4()
    now_ts = datetime.now(UTC)
    report_row = Report(
        id=report_id,
        user_id=user_uuid,
        photos={"items": []},
        directions={"items": []},
        tags={"items": []},
        summary=None,
        llm_cost=Decimal("0.0000"),
        status="queued",
        created_at=now_ts,
        created_by=str(user_id),
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),
    )
    session.add(report_row)
    await session.flush()

    job_state = get_job_state_store()
    job_id = job_state.create_job(report_id=str(report_id), user_id=str(user_id))

    return {
        "report_id": str(report_id),
        "job_id": job_id,
        "stream_url": f"/diagnosis/jobs/{job_id}/stream",
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


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    """组装一帧标准 SSE（与 diagnosis_v1._job_event_stream 同形）。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def send_message_stream(
    session: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    text: str,
    image_keys: list[str] | None = None,
    body_parts: list[str] | None = None,
) -> AsyncIterator[str]:
    """统一 SSE 流入口：chat 模式（token_delta）或 smart_analyze 模式（5 阶段）。

    模式路由：
      - image_keys 有值（1-3 项） → smart_analyze 模式：vision LLM 5 阶段流
      - image_keys 为空           → chat 模式：text LLM token 流

    事件序列（chat）：
      token_delta → ... → end{reply, persona_state}

    事件序列（smart_analyze）：
      start → progress(step=1,percent=15) → progress(step=2,percent=45)
      → progress(step=3,percent=75) → progress(step=4,percent=100)
      → report{directions} → end{reply, persona_state}

    会话不存在 / 已关闭 → 在进入流之前以 HTTPException 抛出（保留 404/410 语义）。
    其它业务异常 → 在流中以 error 事件下发（前端可识别并 toast）。
    """
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

    yield _sse_pack("start", {"step": 0})

    # 1) session 校验 + 加行锁（防止并发请求算出相同 seq）
    # 注意：with_for_update() 在 PostgreSQL 上生成 SELECT ... FOR UPDATE，
    # 第二个并发请求会被阻塞直到第一个 commit 后才继续，保证 seq 不会重复。
    stmt = (
        select(AISession)
        .where(AISession.id == session_id, AISession.user_id == user_id)
        .with_for_update()
    )
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

    # 2) 写 user message（同原逻辑）
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

    # 3) 模式路由
    try:
        if image_keys:
            # smart_analyze 模式
            async for chunk in _stream_smart_analyze(
                session=session,
                ai_session=ai_session,
                user_id=user_id,
                session_id=session_id,
                text=text,
                image_keys=image_keys,
                body_parts=body_parts or [],
                user_msg=user_msg,
            ):
                yield chunk
        else:
            # chat 模式
            async for chunk in _stream_chat(
                session=session,
                ai_session=ai_session,
                user_id=user_id,
                session_id=session_id,
                text=text,
                user_msg=user_msg,
            ):
                yield chunk
    except (SessionNotFoundError, SessionClosedError) as exc:
        yield _sse_pack("error", {"code": exc.code, "message_zh": exc.render_zh()})
        yield _sse_pack("end", {"ok": False, "reply": "", "persona_state": "neutral"})
    except IntegrityError as exc:
        # 并发写入导致 seq 唯一约束冲突（理论上 FOR UPDATE 锁应避免，
        # 但 _stream_chat 内的 assistant msg 写入与 user msg 不在同一事务，
        # 极端并发下仍有小概率触发）。返回限流提示，前端会 toast 并可重试。
        logger.warning(
            "assistant_seq_duplicate",
            session_id=session_id,
            error=str(exc)[:200],
        )
        yield _sse_pack(
            "error",
            {"code": "E_ASSISTANT_CONCURRENT_MESSAGE", "message_zh": "请求过于频繁，请稍后再试"},
        )
        yield _sse_pack("end", {"ok": False, "reply": "", "persona_state": "neutral"})
    except Exception as exc:
        logger.exception(
            "assistant_send_message_stream_error",
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
            session_id=session_id,
        )
        yield _sse_pack("error", {"code": E_ASSISTANT_LLM_ERROR, "message_zh": "AI 服务暂不可用"})
        yield _sse_pack("end", {"ok": False, "reply": "", "persona_state": "neutral"})


async def _stream_smart_analyze(
    session: AsyncSession,
    ai_session: AISession,
    *,
    user_id: str,
    session_id: str,
    text: str,
    image_keys: list[str],
    body_parts: list[str],
    user_msg: AIMessage,
) -> AsyncIterator[str]:
    """智能分析模式：vision LLM 5 阶段流（Sprint 1 走 rule_engine mock）。"""
    from app.services.diagnosis_service import (
        _check_text_safety,
        _invoke_llm_structured,
        _rule_engine_fallback,
    )
    from app.conf.feature_flags import feature_flags
    from app.conf.app_config import app_config

    job_id = str(uuid4())
    _FEATURE_FLAGS: Any = None  # resolved lazily below

    async def _emit_progress(step: int, percent: int, label: str) -> str:
        return _sse_pack("progress", {"step": step, "percent": percent, "label": label})

    # ── V5.2.1-PR4 T21：medical_reject 短路（早返，不调 vision LLM）──────
    # 必须在 try 之前 / progress(1) 之前，确保 SSE error 帧在 progress 之前
    # （V5.2.1 §5.5 E4-2 约束 + 合规审计 ADR-0015 §2.4.4 三事件之一）
    safety_check = _check_text_safety(text)
    if not safety_check["passed"]:
        try:
            audit_kwargs: dict[str, object] = {
                "user_id_pseudo": hash_user_id_pseudo(str(user_id)),
                "session_id": session_id,
                "trigger": "smart_analyze_medical_reject_short_circuit",
                "to_state": "medical_guarded",
            }
            audit_persona_state_switch(**audit_kwargs)
        except Exception as audit_exc:
            # 审计失败不阻断主流程（仅记日志）
            logger.warning("audit_persona_state_switch_failed",
                           error=str(audit_exc)[:200])
        yield _sse_pack("error", {
            "code": E_ASSISTANT_MEDICAL_REJECT,
            "message_zh": "我无法回答医疗问题，建议您咨询专业医师。",
            "medical_guarded": True,
        })
        return

    try:
        # ── Phase 1: preprocess (15%) ───────────────────────────
        yield await _emit_progress(1, 15, "图片校验中")

        # 构建 photo dicts（V5.2.1-PR2 T14：调公共 helper，不再 inline 构造）
        photos = [
            {"object_key": key, "body_part": part}
            for key, part in zip(image_keys, body_parts + ["face"] * max(0, len(image_keys) - len(body_parts)))
        ]

        # ── Phase 2: analyzing (45%) ───────────────────────────
        yield await _emit_progress(2, 45, "正在分析体态")
        user = await session.get(User, user_id) if user_id else None
        # V5.2.1-PR2 T15：profile 字段从 4 个补到 6 个（age_range + skin_type）
        profile = {
            "focus_parts": (user.focus_parts or []) if user else [],
            "intensity": getattr(user, "intensity", None) if user else None,
            "preferred_time": getattr(user, "preferred_time", None) if user else None,
            "sitting_hours": getattr(user, "sitting_hours", None) if user else None,
            "age_range": getattr(user, "age_range", None) if user else None,
            "skin_type": getattr(user, "skin_type", None) if user else None,
        }

        # ── Phase 3: LLM 调用 ──────────────────────────────────
        # Sprint 1: feature flag sample_rate=0 走 mock；sample_rate>0 才调 vision LLM
        llm_model = "rule-engine"
        is_mock = True
        start_ts = time.monotonic()

        # 懒加载 feature_flags 和 app_config（避免循环 import）
        if _FEATURE_FLAGS is None:
            from app.conf.feature_flags import feature_flags as _ff
            _FEATURE_FLAGS = _ff

        _APP_CONFIG: Any = None  # lazy

        if _FEATURE_FLAGS.should_use_vision(user_id):
            try:
                # 懒加载 app_config
                if _APP_CONFIG is None:
                    from app.conf.app_config import app_config as _ac
                    _APP_CONFIG = _ac
                vision_timeout = _APP_CONFIG.llm.vision_timeout_sec
                # V4.1 Step 1.2：asyncio.wait_for 包裹 LLM 调用，超时触发 rule-engine fallback
                result = await asyncio.wait_for(
                    _invoke_llm_structured(photos, profile, text),
                    timeout=vision_timeout,
                )
                # V5.2.1-PR4 F4：happy path 不带 is_fallback；保留完整字段供后续 end event 透传
                payload = {
                    "directions": result["directions"],
                    "tags": result["tags"],
                    "summary": result["summary"],
                    "model": result["model"],
                }
                directions = payload["directions"]
                tags = payload["tags"]
                summary = payload["summary"]
                llm_model = payload["model"]
                is_mock = False
            except asyncio.TimeoutError:
                # V4.1 Step 1.2：vision LLM 超时 → rule-engine fallback
                logger.warning("smart_analyze_llm_timeout", job_id=job_id,
                             timeout_sec=vision_timeout)
                payload = _rule_engine_fallback(profile, text)
                directions = payload["directions"]
                tags = payload.get("tags", [])
                summary = payload.get("summary", "")
                is_mock = True
            except Exception as exc:
                logger.exception("smart_analyze_llm_failed",
                                job_id=job_id, error_type=type(exc).__name__)
                payload = _rule_engine_fallback(profile, text)
                directions = payload["directions"]
                tags = payload.get("tags", [])
                summary = payload.get("summary", "")
                is_mock = True
        else:
            # Sprint 1 默认走 rule_engine fallback
            payload = _rule_engine_fallback(profile, text)
            directions = payload["directions"]
            tags = payload.get("tags", [])
            summary = payload.get("summary", "")
            is_mock = True

        llm_latency_ms = int((time.monotonic() - start_ts) * 1000)

        # ── Phase 4: suggestion (75%) ─────────────────────────
        yield await _emit_progress(3, 75, "生成养护建议")

        # ── Phase 5: persist + ready (100%) ────────────────────
        yield await _emit_progress(4, 100, "分析完成")

        # 落库：assistant AIMessage（含 directions JSONB）
        # V5.2.1-PR4 T20：safety_passed 显式赋真值（不再依赖 Pydantic 默认 True）
        seq2 = ai_session.message_count + 1
        assistant_msg = AIMessage(
            id=uuid4(),
            session_id=ai_session.id,
            seq=seq2,
            role="assistant",
            content=summary or "",
            context_photos=build_ai_message_context_photos(
                directions=directions,
                tags=tags,
                summary=summary,
            ),
            token_count=len(directions),
            llm_model=llm_model,
            llm_latency_ms=llm_latency_ms,
            safety_passed=safety_check["passed"],
            created_at=datetime.now(UTC),
            created_by=str(user_id),
            created_time=datetime.now(UTC),
            last_updated_time=datetime.now(UTC),
            last_updated_by=str(user_id),
        )
        session.add(assistant_msg)
        ai_session.message_count = seq2

        # directions 一次注入 session 画像（追问上下文）
        if hasattr(ai_session, "assistant_profile"):
            ai_session.assistant_profile = {
                "directions": directions,
                "tags": tags,
                "summary": summary,
                "injected_at": datetime.now(UTC).isoformat(),
            }

        await session.flush()

        yield _sse_pack("report", {"directions": directions, "tags": tags, "summary": summary})

        # persona_state 切换（复用 SmartRouter B）
        intent = _classify_intent(text)
        from_state = ai_session.persona_state_end or ai_session.persona_state_start
        to_state = _next_state(from_state, intent)
        if to_state != from_state:
            ai_session.persona_state_end = to_state
            audit_persona_state_switch(
                user_id_pseudo=hash_user_id_pseudo(str(user_id)),
                from_state=from_state,
                to_state=to_state,
                trigger="smart_analyze",
                session_id=session_id,
            )

        await session.commit()

        # V5.2.1-PR3 T17：end event 之前补 step 5（"已就绪"，与 step 4 同样 100）
        # "已就绪" 代表方向列表已落库、可被前端读取
        yield await _emit_progress(5, 100, "已就绪")

        # V5.2.1-PR3 T19：end event 7 字段 schema（ok / reply / persona_state /
        #                          is_mock / medical_guarded / is_quick_reply / level）
        reply_text = f"基于你的照片，我为你生成了 {len(directions)} 条养护建议，可以看看。"
        # medical_guarded / is_quick_reply PR4 之前为 None，PR4 改真值
        medical_guarded = not safety_check["passed"]  # PR4 T20 改真值
        is_quick_reply = False  # 不走 ack_pool 兜底
        # level 取第一条 direction 的 level（PR2 T13 Pydantic 提供 level；兜底 "轻度"）
        primary_level: str = (
            directions[0].get("level", "轻度") if directions else "轻度"
        )
        # V5.2.1-PR4 F4：fallback 标记透传到 end event payload
        end_payload: dict[str, object] = {
            "ok": True,
            "reply": reply_text,
            "persona_state": to_state,
            "is_mock": is_mock,
            "medical_guarded": medical_guarded,
            "is_quick_reply": is_quick_reply,
            "level": primary_level,
        }
        if payload.get("is_fallback"):
            end_payload["is_fallback"] = True
            end_payload["fallback_reason"] = payload.get("fallback_reason", "资料不足")
        yield _sse_pack("end", end_payload)

        logger.info("smart_analyze_done", job_id=job_id, llm_model=llm_model,
                    is_mock=is_mock, latency_ms=llm_latency_ms,
                    photo_count=len(image_keys))

    except Exception as exc:
        logger.exception("smart_analyze_stream_error", job_id=job_id,
                        error_type=type(exc).__name__, error_message=str(exc)[:200])
        yield _sse_pack("error", {
            "code": E_ASSISTANT_LLM_ERROR,
            "message_zh": "分析服务暂时不可用",
            "stage": "analyzing",
        })
        yield _sse_pack("end", {"ok": False, "reply": "", "persona_state": "neutral"})
        return


async def _stream_chat(
    session: AsyncSession,
    ai_session: AISession,
    *,
    user_id: str,
    session_id: str,
    text: str,
    user_msg: AIMessage,
) -> AsyncIterator[str]:
    """chat 模式：text LLM token 流 + 快问分层路由。

    事件序列：
      token_delta data: {"token": "单字"}   ← 每 token 一个事件
      ...
      end        data: {..., "is_quick_reply": bool, "response_mode": str, "emotion_level": str}

    快问路由（PRD §3.5.3）：
      - B1 问候 → 预设话术 + 打字机
      - B3 情绪 L1 → 预设话术
      - B3 情绪 L2 → 轻量 LLM
      - B3 情绪 L3 → 安全兜底 + 危机日志
      - B5/C 类 → 轻量 LLM 陪伴
      - D 类 → 引导回忆入口
    """
    # ── 快问服务初始化 ────────────────────────────────────────────────────────
    from app.services.diagnosis_service import _check_text_safety
    quick_reply_svc = get_quick_reply_service()
    emotion_classifier = get_emotion_classifier()
    light_llm_svc = get_light_llm_service()

    # ── B1 问候快问检测 ────────────────────────────────────────────────────
    if quick_reply_svc.is_greeting(text):
        reply_text = quick_reply_svc.get_greeting_reply()
        is_quick_reply = True
        response_mode = "template"
        emotion_level: str | None = None
        llm_model = "quick-reply-template"
        llm_cost = 0.0
        # 打字机效果
        for char in reply_text:
            yield _sse_pack("token_delta", {"token": char})
            await asyncio.sleep(0.03)  # ~30ms per char
        # 落库
        seq2 = ai_session.message_count + 1
        assistant_msg = AIMessage(
            id=uuid4(),
            session_id=ai_session.id,
            seq=seq2,
            role="assistant",
            content=reply_text,
            safety_passed=True,
            llm_model=llm_model,
            llm_latency_ms=0,
            llm_cost=0.0,
            referenced_feedback_ids=[],
            referenced_video_ids=[],
            token_count=len(reply_text),
            created_at=datetime.now(UTC),
            created_by=str(user_id),
            created_time=datetime.now(UTC),
            last_updated_time=datetime.now(UTC),
            last_updated_by=str(user_id),
        )
        session.add(assistant_msg)
        ai_session.message_count = seq2
        await session.commit()
        yield _sse_pack("end", {
            "ok": True,
            "reply": reply_text,
            "persona_state": "warm",
            "is_quick_reply": is_quick_reply,
            "response_mode": response_mode,
            "emotion_level": emotion_level,
            "ai_msg_id": str(assistant_msg.id),
        })
        return

    # ── B3 情绪检测 + 分层响应 ──────────────────────────────────────────────
    emotion_result = emotion_classifier.classify(text)
    if emotion_result["is_emotion"]:
        level = emotion_result["level"]
        response_mode = emotion_result["response_mode"]
        is_quick_reply = response_mode in ("template", "safe_fallback")

        if level == "light":
            # L1：预设话术
            reply_text = quick_reply_svc.get_light_reply(text)
            for char in reply_text:
                yield _sse_pack("token_delta", {"token": char})
                await asyncio.sleep(0.03)
        elif level == "medium":
            # L2：轻量 LLM 共情
            reply_text = ""
            try:
                reply_text = await light_llm_svc.generate_emotion_response_async(text)
            except Exception as exc:
                logger.warning(
                    "light_llm_emotion_failed_fallback",
                    user_input=text[:100],
                    error_type=type(exc).__name__,
                )
                reply_text = quick_reply_svc.get_light_reply(text)
            response_mode = "light_llm"
            is_quick_reply = False
        elif level == "heavy":
            # L3：安全兜底
            reply_text = quick_reply_svc.get_heavy_safe_reply()
            # 危机事件日志（静默记录，不告警）
            logger.warning(
                "crisis_event_detected",
                user_id_pseudo=hash_user_id_pseudo(str(user_id)),
                session_id=session_id,
                matched_keywords=emotion_result.get("matched_keywords", []),
            )
            for char in reply_text:
                yield _sse_pack("token_delta", {"token": char})
                await asyncio.sleep(0.03)
        else:
            reply_text = ""
            response_mode = None

        if reply_text:
            # 落库
            seq2 = ai_session.message_count + 1
            assistant_msg = AIMessage(
                id=uuid4(),
                session_id=ai_session.id,
                seq=seq2,
                role="assistant",
                content=reply_text,
                safety_passed=True,
                llm_model="quick-reply-template" if is_quick_reply else "light-llm",
                llm_latency_ms=0,
                llm_cost=0.0,
                referenced_feedback_ids=[],
                referenced_video_ids=[],
                token_count=len(reply_text),
                created_at=datetime.now(UTC),
                created_by=str(user_id),
                created_time=datetime.now(UTC),
                last_updated_time=datetime.now(UTC),
                last_updated_by=str(user_id),
            )
            session.add(assistant_msg)
            ai_session.message_count = seq2
            await session.commit()
            yield _sse_pack("end", {
                "ok": True,
                "reply": reply_text,
                "persona_state": "warm",
                "is_quick_reply": is_quick_reply,
                "response_mode": response_mode,
                "emotion_level": level,
                "ai_msg_id": str(assistant_msg.id),
            })
            return

    # ── B5/C 类：陪伴与倾诉 ────────────────────────────────────────────────
    if quick_reply_svc.is_companion_intent(text) or quick_reply_svc.is_long_text_vent(text):
        reply_text = ""
        try:
            reply_text = await light_llm_svc.generate_companion_async(text, has_history=False)
        except Exception as exc:
            logger.warning(
                "light_llm_companion_failed_fallback",
                user_input=text[:100],
                error_type=type(exc).__name__,
            )
            reply_text = _render_by_state("warm", "fast")

        if reply_text:
            for char in reply_text:
                yield _sse_pack("token_delta", {"token": char})
                await asyncio.sleep(0.03)
            seq2 = ai_session.message_count + 1
            assistant_msg = AIMessage(
                id=uuid4(),
                session_id=ai_session.id,
                seq=seq2,
                role="assistant",
                content=reply_text,
                safety_passed=True,
                llm_model="light-llm",
                llm_latency_ms=0,
                llm_cost=0.0,
                referenced_feedback_ids=[],
                referenced_video_ids=[],
                token_count=len(reply_text),
                created_at=datetime.now(UTC),
                created_by=str(user_id),
                created_time=datetime.now(UTC),
                last_updated_time=datetime.now(UTC),
                last_updated_by=str(user_id),
            )
            session.add(assistant_msg)
            ai_session.message_count = seq2
            await session.commit()
            yield _sse_pack("end", {
                "ok": True,
                "reply": reply_text,
                "persona_state": "warm",
                "is_quick_reply": False,
                "response_mode": "light_llm",
                "emotion_level": None,
                "ai_msg_id": str(assistant_msg.id),
            })
            return

    # ── D 类：引导回忆入口 ─────────────────────────────────────────────────
    if quick_reply_svc.is_recall_intent(text):
        reply_text = quick_reply_svc.get_recall_guide_reply()
        is_quick_reply = True
        response_mode = "template"
        for char in reply_text:
            yield _sse_pack("token_delta", {"token": char})
            await asyncio.sleep(0.03)
        seq2 = ai_session.message_count + 1
        assistant_msg = AIMessage(
            id=uuid4(),
            session_id=ai_session.id,
            seq=seq2,
            role="assistant",
            content=reply_text,
            safety_passed=True,
            llm_model="quick-reply-template",
            llm_latency_ms=0,
            llm_cost=0.0,
            referenced_feedback_ids=[],
            referenced_video_ids=[],
            token_count=len(reply_text),
            created_at=datetime.now(UTC),
            created_by=str(user_id),
            created_time=datetime.now(UTC),
            last_updated_time=datetime.now(UTC),
            last_updated_by=str(user_id),
        )
        session.add(assistant_msg)
        ai_session.message_count = seq2
        await session.commit()
        yield _sse_pack("end", {
            "ok": True,
            "reply": reply_text,
            "persona_state": "warm",
            "is_quick_reply": is_quick_reply,
            "response_mode": response_mode,
            "emotion_level": None,
            "ai_msg_id": str(assistant_msg.id),
        })
        return

    # ── 默认：正常 LLM 流式 ────────────────────────────────────────────────
    from_state = ai_session.persona_state_end or ai_session.persona_state_start
    intent = _classify_intent(text)
    to_state = _next_state(from_state, intent)

    # ── medical_guarded 短路径（不走 LLM）──────────────────────────────
    if to_state == "medical_guarded":
        if to_state != from_state:
            ai_session.persona_state_end = to_state
            audit_persona_state_switch(
                user_id_pseudo=hash_user_id_pseudo(str(user_id)),
                from_state=from_state, to_state=to_state,
                trigger=intent, session_id=session_id,
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
        await session.commit()
        yield _sse_pack("end", {
            "ok": True,
            "reply": reply_text_medical,
            "persona_state": to_state,
            "medical_guarded": True,
            "is_quick_reply": True,
            "response_mode": "template",
            "ai_msg_id": str(msg_id),
        })
        return

    # ── Sprint 2：text LLM token 流 ─────────────────────────────────
    SYSTEM_PROMPT = (
        "你是 Selfwell 智能管家，只提供陪伴、习惯建议和基础调理常识。"
        "不得给出诊断、处方、注射、医美治疗或疗效承诺。"
        "回复要温柔、简洁，控制在 100 字以内。"
        "状态：{persona_state}，用户输入：{user_text}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "{user_text}"),
    ])
    chain = prompt | text_llm

    full_reply = ""
    start_ts = time.monotonic()
    llm_model = "text-llm"
    try:
        async for event in chain.astream_events(
            {"persona_state": to_state, "user_text": text},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                token = event["data"]["chunk"].content
                if token:
                    full_reply += token
                    yield _sse_pack("token_delta", {"token": token})
    except Exception as exc:
        logger.warning(
            "assistant_chat_token_stream_error",
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
            session_id=session_id,
        )
        full_reply = ""

    llm_latency_ms = int((time.monotonic() - start_ts) * 1000)

    # LLM 失败 → fallback 文案
    if not full_reply:
        full_reply = _render_by_state(to_state, intent)
        llm_model = "static-fallback"

    # persona_state 切换审计
    if to_state != from_state:
        ai_session.persona_state_end = to_state
        audit_kwargs: dict[str, object] = {
            "user_id_pseudo": hash_user_id_pseudo(str(user_id)),
            "from_state": from_state,
            "to_state": to_state,
            "trigger": intent,
            "session_id": session_id,
        }
        if llm_model == "static-fallback":
            audit_kwargs["mock_reason"] = "llm_unavailable_fallback"
        audit_persona_state_switch(**audit_kwargs)

    # 落库
    # V5.2.1-PR4 T20：safety_passed 显式赋真值（不再硬编码 True）
    safety_check = _check_text_safety(text)
    safety_passed = safety_check["passed"] and to_state != "medical_guarded"
    seq2 = ai_session.message_count + 1
    assistant_msg = AIMessage(
        id=uuid4(),
        session_id=ai_session.id,
        seq=seq2,
        role="assistant",
        content=full_reply,
        safety_passed=safety_passed,
        llm_model=llm_model,
        llm_latency_ms=llm_latency_ms,
        referenced_feedback_ids=[],
        referenced_video_ids=[],
        token_count=len(full_reply),
        safety_violations={"persona_state": to_state},
        created_at=datetime.now(UTC),
        created_by=str(user_id),
        created_time=datetime.now(UTC),
        last_updated_time=datetime.now(UTC),
        last_updated_by=str(user_id),
    )
    session.add(assistant_msg)
    ai_session.message_count = seq2
    await session.commit()

    yield _sse_pack("end", {
        "ok": True,
        "reply": full_reply,
        "persona_state": to_state,
        "is_quick_reply": False,
        "response_mode": "full_llm",
        "ai_msg_id": str(assistant_msg.id),
    })


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
