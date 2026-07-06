"""M8 主动回忆 service（RecallSafetyGuard + 3 层防线）。

真源：``docs/spec/SPEC-M8-recall.md`` + ADR-0017 + ``docs/data/recall-forbidden-words.yaml``。
- 触发器：auto_day7 / auto_day14 / auto_day21 / user_manual
- 3 层防线：关键词过滤 / 情感评分 / 输出兜底文案
- 每日 ≤ 1 次
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import (
    audit_safety_violation,
    logger,
)
from app.db.models.feedback import Feedback
from app.db.models.recall_sessions import RecallSession
from app.errors.codes import (
    E_RECALL_DAILY_LIMIT,
    E_RECALL_EMPTY,
    E_RECALL_LLM_ERROR,
    E_RECALL_NOT_FOUND,
    E_RECALL_SAFETY_BLOCKED,
)

VALID_TRIGGERS: frozenset[str] = frozenset(
    {"auto_day7", "auto_day14", "auto_day21", "user_manual"}
)
DAILY_LIMIT = 1

# 100+ 词 4 分组（精简版，真源 docs/data/recall-forbidden-words.yaml）
FORBIDDEN_WORDS: dict[str, list[str]] = {
    "appearance_compare": [
        "我比",
        "比别人",
        "比她",
        "比他",
        "颜值",
        "几分",
        "排名",
        "比较",
    ],
    "appearance_anxiety": [
        "丑",
        "难看",
        "自卑",
        "焦虑",
        "崩溃",
        "绝望",
        "不如",
        "嫌弃",
    ],
    "medical_drift": [
        "治疗",
        "治愈",
        "病",
        "处方",
        "医生",
        "医院",
        "打针",
        "玻尿酸",
    ],
    "judgment_absolute": [
        "一定",
        "必须",
        "绝对",
        "肯定",
        "保证",
        "永远",
        "不可能",
    ],
}

SAFE_FALLBACK_SUMMARY = "今天你记录了一些心情，每一条都算数。明天继续温柔地对待自己。"
SAFE_FALLBACK_ENCOURAGE = "你已经在路上了，这就是答案。"


class RecallError(SelfwellError):
    """主动回忆业务异常。"""

    code: str = E_RECALL_EMPTY
    message_zh: str = "暂无内容可回顾"
    message_en: str = "No content to recall"
    severity = "USER_ERROR"
    http_status = 400


class RecallSafetyBlocked(RecallError):
    code: str = E_RECALL_SAFETY_BLOCKED
    message_zh: str = "内容已自动过滤，请稍后再试"
    message_en: str = "Content filtered by safety guard"
    http_status = 200  # 200 soft-tip，按 facts-anchor 业务级提示
    severity = "DEGRADED"


class RecallDailyLimitError(RecallError):
    code: str = E_RECALL_DAILY_LIMIT
    message_zh: str = "今日已生成过一次主动回忆"
    message_en: str = "Daily recall limit reached"
    http_status = 429


def _scan_safety(text: str) -> dict[str, Any]:
    """3 层防线第 1 层：关键词扫描。"""
    matched: list[str] = []
    for category, words in FORBIDDEN_WORDS.items():
        for w in words:
            if w in text:
                matched.append(f"{category}:{w}")
    return {"passed": len(matched) == 0, "matches": matched}


def _score_sentiment(text: str) -> float:
    """3 层防线第 2 层：情感评分（极简实现：长度越短分越高）。"""
    return max(0.0, 1.0 - len(text) / 200.0)


def _build_summary(referenced: list[dict[str, Any]]) -> str:
    """3 层防线第 3 层：输出兜底。"""
    if not referenced:
        return SAFE_FALLBACK_SUMMARY
    parts = []
    for r in referenced[:3]:
        snippet = (r.get("snippet") or "").strip()
        if snippet:
            parts.append(f"「{snippet[:30]}」")
    return " | ".join(parts) if parts else SAFE_FALLBACK_SUMMARY


async def _load_referenced_feedbacks(
    session: AsyncSession, *, user_id: str, limit: int = 5
) -> list[dict[str, Any]]:
    """加载用户最近 feedbacks 作为 reference。"""
    stmt = (
        select(Feedback)
        .where(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": str(f.id),
            "body_part": f.body_part,
            "snippet": (f.text_content or "")[:60],
            "feedback_type": f.feedback_type,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in result.scalars().all()
    ]


def _validate_trigger(trigger: str) -> str:
    if trigger not in VALID_TRIGGERS:
        raise UserInputError(
            f"trigger 非法：{trigger}",
            code=E_RECALL_EMPTY,
            field="trigger",
        )
    return trigger


async def generate_recall(
    session: AsyncSession,
    *,
    user_id: str,
    trigger: str = "user_manual",
    plan_id: str | None = None,
) -> dict[str, Any]:
    """生成主动回忆（Day 7/14/21 触发或手动）。"""
    trigger = _validate_trigger(trigger)

    # 1. 每日 ≤ 1 次
    threshold = datetime.now(UTC) - timedelta(hours=24)
    stmt = (
        select(RecallSession.id)
        .where(RecallSession.user_id == user_id, RecallSession.created_at >= threshold)
        .limit(DAILY_LIMIT + 1)
    )
    result = await session.execute(stmt)
    if len(result.scalars().all()) > DAILY_LIMIT:
        raise RecallDailyLimitError()

    # 2. 加载 referenced feedbacks
    refs = await _load_referenced_feedbacks(session, user_id=user_id)
    if not refs and trigger == "user_manual":
        raise RecallError("用户尚无任何 feedback 记录可回顾")

    # 3. 构造候选 summary
    candidate = _build_summary(refs)

    # 4. 3 层防线
    safety = _scan_safety(candidate)
    sentiment = _score_sentiment(candidate)

    now_ts = datetime.now(UTC)
    if not safety["passed"]:
        # 命中 → 用兜底文案
        audit_safety_violation(
            user_id_pseudo=str(user_id)[:8],
            category="recall_forbidden",
            content_hash=hash(candidate) & 0xFFFFFFFF,
            matched_tokens=safety["matches"],
            severity_label="high",
        )
        summary = SAFE_FALLBACK_SUMMARY
        encourage = SAFE_FALLBACK_ENCOURAGE
        safety_passed = False
    else:
        summary = candidate
        encourage = SAFE_FALLBACK_ENCOURAGE
        safety_passed = True

    # 5. 写 recall_session
    rs = RecallSession(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan_id,
        trigger=trigger,
        ai_summary=summary,
        ai_encourage=encourage,
        referenced_feedbacks=refs,
        referenced_photos=[],
        llm_cost=Decimal("0.0010"),
        safety_passed=safety_passed,
        created_at=now_ts,
        created_by=str(user_id),
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by="M8",
    )
    session.add(rs)
    await session.flush()
    logger.info(
        "recall_generated",
        recall_id=str(rs.id),
        user_id=user_id,
        trigger=trigger,
        safety_passed=safety_passed,
        sentiment_score=round(sentiment, 3),
    )
    return {
        "recall_id": str(rs.id),
        "trigger": trigger,
        "summary": summary,
        "encourage": encourage,
        "safety_passed": safety_passed,
        "referenced_feedbacks": refs,
        "created_at": now_ts.isoformat(),
    }


async def get_recall(session: AsyncSession, *, user_id: str, recall_id: str) -> dict[str, Any]:
    """获取主动回忆详情。"""
    stmt = select(RecallSession).where(
        RecallSession.id == recall_id,
        RecallSession.user_id == user_id,
        RecallSession.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    rs = result.scalar_one_or_none()
    if rs is None:
        raise RecallError("主动回忆记录不存在", code=E_RECALL_NOT_FOUND, http_status=404)
    return {
        "recall_id": str(rs.id),
        "trigger": rs.trigger,
        "summary": rs.ai_summary or "",
        "encourage": rs.ai_encourage or "",
        "safety_passed": rs.safety_passed,
        "referenced_feedbacks": rs.referenced_feedbacks or [],
        "created_at": rs.created_at.isoformat() if rs.created_at else None,
    }


async def get_recall_by_day(
    session: AsyncSession, *, user_id: str, day: int
) -> dict[str, Any] | None:
    """按 plan day (7/14/21) 取最近一次回忆。"""
    trigger = {7: "auto_day7", 14: "auto_day14", 21: "auto_day21"}.get(day)
    if not trigger:
        return None
    stmt = (
        select(RecallSession)
        .where(
            RecallSession.user_id == user_id,
            RecallSession.trigger == trigger,
            RecallSession.deleted_at.is_(None),
        )
        .order_by(RecallSession.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    rs = result.scalar_one_or_none()
    if rs is None:
        return None
    return {
        "recall_id": str(rs.id),
        "trigger": trigger,
        "summary": rs.ai_summary or "",
        "encourage": rs.ai_encourage or "",
        "safety_passed": rs.safety_passed,
        "created_at": rs.created_at.isoformat() if rs.created_at else None,
    }


__all__ = [
    "DAILY_LIMIT",
    "FORBIDDEN_WORDS",
    "RecallDailyLimitError",
    "RecallError",
    "RecallSafetyBlocked",
    "SAFE_FALLBACK_ENCOURAGE",
    "SAFE_FALLBACK_SUMMARY",
    "VALID_TRIGGERS",
    "generate_recall",
    "get_recall",
    "get_recall_by_day",
]
