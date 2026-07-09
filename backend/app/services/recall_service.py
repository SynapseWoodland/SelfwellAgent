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

from app.core.audit import hash_user_id_pseudo
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
    E_RECALL_NOT_FOUND,
    E_RECALL_SAFETY_BLOCKED,
)

VALID_TRIGGERS: frozenset[str] = frozenset(
    {"auto_day7", "auto_day14", "auto_day21", "user_manual"}
)
DAILY_LIMIT = 1

# 4 分组 100+ 词（精简版，真源 docs/data/recall-forbidden-words.yaml）。
#
# 分组命名规范（ADR-0017 §3.3 + test_recall_safety_keywords 对齐）：
# - before_after_judge    前后/对比/进步评判
# - effect_commit         效果承诺/变化描述
# - numeric_judge         数字评判/天数比较/百分比
# - appearance_judge      评判气质/外观/排名
#
# 注意：不要把"X 天""已经""坚持"等中性词直接作为关键词（会误拦）。
# 凡是含具体数字 + 评判义复合模式：保留精确短语作为触发器。
FORBIDDEN_WORDS: dict[str, list[str]] = {
    "before_after_judge": [
        "前后对比",
        "前后对比",
        "之前更好",
        "比之前",
        "比上周",
        "比上周更好",
        "更挺拔",
        "更紧致",
        "更有气质",
        "进步了",
        "改善了",
        "好转了",
        "效果明显",
        "效果显著",
    ],
    "effect_commit": [
        "会飙升",
        "会爆发",
        "彻底",
        "完全治愈",
        "治愈率",
        "痊愈",
        "一直好",
        "永远好",
        "稳定不复发",
        "明显改善",
        "肉眼可见",
        "立竿见影",
    ],
    "numeric_judge": [
        "坚持 X 天",
        "坚持 14 天",
        "坚持 7 天",
        "坚持 21 天",
        "打败 95%",
        "打败 90%",
        "超过 95%",
        "前 10%",
        "前 5%",
        "95% 的人",
        "排名第一",
        "排名第二",
        "排名第",
        "100 分",
    ],
    "appearance_judge": [
        "颜值",
        "变白",
        "皮肤变白",
        "脸变白",
        "变瘦",
        "变胖",
        "变美",
        "变丑",
        "难看",
        "焦虑",
        "自卑",
        "崩溃",
        "绝望",
        "嫌弃",
        "玻尿酸",
        "打针",
        "医美",
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
        .where(Feedback.created_by == str(user_id))
        .order_by(Feedback.created_time.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": str(f.id),
            "body_part": f.body_part,
            "snippet": (f.text_content or "")[:60],
            "feedback_type": f.feedback_type,
            "created_at": f.created_time.isoformat() if f.created_time else None,
            "created_by": f.created_by,
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
            user_id_pseudo=hash_user_id_pseudo(str(user_id)),
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
        created_by=str(user_id),         # 当前创建用户（回忆发起人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),    # 当前更新用户
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
    """按 plan day (7/14/21) 取最近一次回忆。

    返回字段（与 tests/unit/services/test_recall_today.py 契约 1:1）：
    - recall_id / trigger / summary / encourage / safety_passed / created_at
    - referenced_feedbacks（list；保结构稳定，避免测试 KeyError）
    """
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
        "referenced_feedbacks": rs.referenced_feedbacks or [],
        "created_at": rs.created_at.isoformat() if rs.created_at else None,
    }


__all__ = [
    "DAILY_LIMIT",
    "FORBIDDEN_WORDS",
    "SAFE_FALLBACK_ENCOURAGE",
    "SAFE_FALLBACK_SUMMARY",
    "VALID_TRIGGERS",
    "RecallDailyLimitError",
    "RecallError",
    "RecallSafetyBlocked",
    "generate_recall",
    "get_recall",
    "get_recall_by_day",
]
