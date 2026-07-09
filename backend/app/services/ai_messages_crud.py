"""assistant_msg 落库（决策 3：on end 整体落库，单事务）。

真源：
  - ``backend/app/services/assistant_service.py::send_message_stream``（PR-A2 worker C 落地）
  - ``docs/data/data-dictionary.md`` §D.4 ``ai_messages`` 表 DDL
  - ``backend/app/db/models/ai_messages.py`` AIMessage ORM

设计约束（与现有 DDL 1:1，不引入 schema migration）：
  - 主字段写 SQLAlchemy 真列（content / role / safety_passed / llm_model / llm_cost / trigger）
  - 决策 3 任务列出的 ``directions`` / ``persona_state`` / ``medical_guarded`` 等"扩展元信息"
    在现有 DDL 中**没有对应列**。为避免引入 DDL migration，本模块把此类扩展写入
    ``AIMessage.safety_violations`` JSONB（仅当有扩展内容时）。该字段语义上"安全/审计相关
    结构化元信息"，可承载此职责；若后续需要独立列，需走 Alembic migration（见
    ``docs/plan/to-be-clarified.md`` 待办，由父 agent 跟进，不在本 worker 范围）。

调用时机：``assistant_service.send_message_stream`` 在 yield ``end`` 帧之前，await 调用
本模块的 ``persist_assistant_message``；ai_msg.id 通过 end.data.ai_msg_id 回执前端。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import logger
from app.db.models.ai_messages import AIMessage


async def persist_assistant_message(  # noqa: PLR0913 — service constructor needs 14 kwargs (matches AIMessage schema)
    session: AsyncSession,
    *,
    session_uuid: UUID,
    user_id: str,
    seq: int,
    content: str,
    safety_passed: bool,
    llm_model: str | None,
    llm_cost: float,
    trigger: str | None = None,
    intent: str | None = None,
    # 决策 3 扩展元信息（无独立列时，写入 safety_violations JSONB）
    directions: list[dict[str, Any]] | None = None,
    persona_state: str | None = None,
    medical_guarded: bool = False,
    llm_latency_ms: int | None = None,
    token_count: int | None = None,
) -> UUID:
    """End-frame 触发时调用，整条消息一次落库。

    Args:
        session: 数据库 AsyncSession（已绑定事务，由调用方 commit）。
        session_uuid: ai_sessions.id（UUID）。
        user_id: 当前 user_id（audit 字段 created_by 取 str(user_id)）。
        seq: 会话内序号（递增）。
        content: 拼接后的回复全文。
        safety_passed: 是否通过安全检查；medical_guarded=True 时强制 False。
        llm_model: LLM 模型标识，未调 LLM 时为 ``"static-fallback"`` / ``"sse-mock-fallback"``。
        llm_cost: 累计 LLM 成本（元）。
        trigger: 触发来源枚举（user_input / smart_router / medical_reject / safety_fallback ...）。
        intent: 该条消息的具体 intent。
        directions: PR-A2 report 帧携带的 3 个养护方向列表（无独立 JSONB 列，
            有值时与 persona_state/medical_guarded 一起写入 safety_violations）。
        persona_state: 会话末态 persona_state（无独立列，写入 safety_violations）。
        medical_guarded: 是否 medical_guarded 吸收态（无独立列，写入 safety_violations）。
        llm_latency_ms: LLM 延迟毫秒（可选）。
        token_count: token 计数（可选，默认取 len(content)）。

    Returns:
        新插入消息的 ``AIMessage.id``（UUID）。

    Note:
        本函数**只 append + flush**，**不 commit**。commit 由调用方 / FastAPI dependency
        ``get_db`` 在请求结束时统一管理，避免在流式 generator 中 commit 引发"流已关闭"
        时 commit 失败的边界问题。

    """
    # medical_guarded=True → safety_passed 必须为 False
    # （决策 3 + TBC-009 §10.4 第 9 条告警义务）
    if medical_guarded:
        safety_passed = False

    extra_metadata: dict[str, Any] = {}
    if directions:
        extra_metadata["directions"] = directions
    if persona_state:
        extra_metadata["persona_state"] = persona_state
    if medical_guarded:
        extra_metadata["medical_guarded"] = True

    # 仅当有扩展元信息时填 safety_violations（保留语义聚焦；medical_guarded=True
    # 时同时携带 persona_state 与 directions 摘要，便于审计 trace）
    safety_violations: dict[str, Any] | None = extra_metadata or None

    if token_count is None:
        token_count = len(content) if content else 0

    now_ts = _utcnow()
    msg_id = uuid4()
    msg = AIMessage(
        id=msg_id,
        session_id=session_uuid,
        seq=seq,
        role="assistant",
        content=content,
        trigger=trigger,
        intent=intent,
        llm_cost=_decimal_from_float(llm_cost),
        llm_model=llm_model,
        llm_latency_ms=llm_latency_ms,
        safety_passed=safety_passed,
        safety_violations=safety_violations,
        token_count=token_count,
        referenced_feedback_ids=[],
        referenced_video_ids=[],
        created_at=now_ts,
        created_by=str(user_id),
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),
    )
    session.add(msg)
    await session.flush()

    logger.info(
        "assistant_msg_persisted",
        msg_id=str(msg_id),
        session_id=str(session_uuid),
        user_id=user_id,
        seq=seq,
        safety_passed=safety_passed,
        medical_guarded=medical_guarded,
        persona_state=persona_state,
        llm_model=llm_model,
        directions_count=len(directions) if directions else 0,
    )
    return msg_id


def _utcnow() -> Any:
    """UTC now helper (延迟导入避免循环引用)."""
    from datetime import UTC, datetime  # intentional lazy import

    return datetime.now(UTC)


def _decimal_from_float(value: float) -> Any:
    """Decimal(10,4) 精度适配（AIMessage.llm_cost 列强约束）。"""
    from decimal import Decimal  # intentional lazy import

    return Decimal(f"{float(value):.4f}")


__all__ = ["persist_assistant_message"]
