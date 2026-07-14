"""M7 心情日记 / 多部位反馈 service。

真源：``docs/spec/SPEC-M7-feedback.md`` + ADR-0016 + ``docs/data/body-parts.yaml``。
- 4 种 feedback_type：mood_text / mood_photo / period_photo / plan_compare_photo
- 30 条 ACK 池（``docs/data/ack-pool.yaml``）
- 合规审查
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models.feedback import Feedback
from app.errors.codes import (
    E_FEEDBACK_BODY_PART_REQUIRED,
    E_FEEDBACK_DAILY_LIMIT,
    E_FEEDBACK_INVALID_TYPE,
    E_FEEDBACK_PAYLOAD_MISMATCH,
    E_FEEDBACK_PHOTO_TOO_LARGE,
    E_FEEDBACK_PHOTO_URL_REQUIRED,
    E_FEEDBACK_TEXT_TOO_LONG,
)

# 4 种 feedback_type（与 facts-anchor §2.7 一致）
FEEDBACK_TYPES: frozenset[str] = frozenset(
    {"mood_text", "mood_photo", "period_photo", "plan_compare_photo"}
)
# 6 部位（与 body-parts.yaml 一致）
BODY_PARTS: frozenset[str] = frozenset(
    {"face", "head", "shoulder_neck", "waist", "leg", "overall_look"}
)
# 允许的 photo body_parts（含 unclassified）
PHOTO_BODY_PARTS: frozenset[str] = BODY_PARTS | {"unclassified"}
# 不需要 body_part 的类型（仅文本）
TEXT_ONLY_TYPES: frozenset[str] = frozenset({"mood_text"})

MAX_TEXT_LENGTH = 500
MAX_DAILY_LIMIT = 5
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10MB

# 30 条 ACK 池（精简版，真源 docs/data/ack-pool.yaml）
_ACK_POOL: list[str] = [
    "谢谢你愿意记录，每一次表达都是自我关怀。",
    "我在这里陪着你，慢慢来。",
    "你的感受很重要，我认真看了。",
    "今天能记录本身就是一件很棒的事。",
    "别忘了给自己一个拥抱。",
    "能看到自己的变化，已经很了不起。",
    "坚持本身就是一种力量。",
    "你的努力我都看在眼里。",
    "温柔一点对待自己，你值得。",
    "不需要完美，真诚就好。",
    "今天又往前迈了一小步。",
    "辛苦了，先喝口水吧。",
    "我为你感到骄傲。",
    "你的节奏刚刚好。",
    "哪怕只是小小的一个动作，也算数。",
    "成长从来不是直线，偶尔的起伏很正常。",
    "休息也是进步的一部分。",
    "我在你身后，一直都在。",
    "记录下来，就是对未来的自己最好的礼物。",
    "今天也请多爱自己一点点。",
    "你已经做得很好了。",
    "别着急，花总会开的。",
    "温柔而坚定地走下去。",
    "每一个今天都在为明天打基础。",
    "你比自己想象的更勇敢。",
    "允许自己慢一点，没关系的。",
    "你已经在路上了，这就是答案。",
    "小小的进步也是进步。",
    "感谢你愿意让我陪着你。",
    "愿你今天多一点轻松，少一点紧绷。",
]


class FeedbackError(SelfwellError):
    """心情日记 / 反馈业务异常。"""

    code: str = E_FEEDBACK_INVALID_TYPE
    message_zh: str = "反馈请求无效"
    message_en: str = "Invalid feedback request"
    severity = "USER_ERROR"
    http_status = 400


class FeedbackDailyLimitError(FeedbackError):
    code: str = E_FEEDBACK_DAILY_LIMIT
    message_zh: str = "今日反馈已达上限"
    message_en: str = "Daily feedback limit reached"
    http_status = 429


def pick_ack(seed: int | None = None) -> str:
    """从 30 条 ACK 池里挑一条（可指定 seed）。"""
    if seed is None:
        return _ACK_POOL[0]
    return _ACK_POOL[seed % len(_ACK_POOL)]


def validate_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    """校验 feedback payload。返回标准化 dict。"""
    ftype = payload.get("feedback_type")
    if ftype not in FEEDBACK_TYPES:
        raise UserInputError(
            f"feedback_type 非法：{ftype}",
            code=E_FEEDBACK_INVALID_TYPE,
            field="feedback_type",
        )

    text = payload.get("text_content")
    if ftype in TEXT_ONLY_TYPES:
        if not text:
            raise UserInputError(
                f"{ftype} 必须提供 text_content",
                code=E_FEEDBACK_PAYLOAD_MISMATCH,
                field="text_content",
            )
    if text is not None and len(text) > MAX_TEXT_LENGTH:
        raise FeedbackError(
            f"text_content 超长（{len(text)} > {MAX_TEXT_LENGTH}）",
            code=E_FEEDBACK_TEXT_TOO_LONG,
            field="text_content",
            limit=MAX_TEXT_LENGTH,
        )

    photo_url = payload.get("photo_url")
    if ftype != "mood_text":
        if not photo_url:
            raise FeedbackError(
                f"{ftype} 必须提供 photo_url",
                code=E_FEEDBACK_PHOTO_URL_REQUIRED,
                field="photo_url",
            )
        size = int(payload.get("photo_size_bytes", 0) or 0)
        if size > MAX_PHOTO_BYTES:
            raise FeedbackError(
                f"照片过大（{size // (1024 * 1024)}MB）",
                code=E_FEEDBACK_PHOTO_TOO_LARGE,
                field="photo_size_bytes",
            )

    body_part = payload.get("body_part")
    if ftype != "mood_text" and body_part is None:
        raise FeedbackError(
            f"{ftype} 必须提供 body_part（6 部位 + unclassified）",
            code=E_FEEDBACK_BODY_PART_REQUIRED,
            field="body_part",
        )
    if body_part is not None and body_part not in PHOTO_BODY_PARTS:
        raise FeedbackError(
            f"body_part 非法：{body_part}",
            code=E_FEEDBACK_BODY_PART_REQUIRED,
            field="body_part",
        )

    return {
        "feedback_type": ftype,
        "text_content": text,
        "photo_url": photo_url,
        "body_part": body_part,
    }


async def create_feedback(
    session: AsyncSession,
    *,
    user_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """创建 feedback 记录 + 返回 ACK。"""
    data = validate_feedback(payload)

    # 每日上限（最近 24h 5 条）
    # Feedback 表 audit 字段：created_by + created_time（无 created_at）
    from datetime import timedelta

    threshold = datetime.now(UTC) - timedelta(hours=24)
    stmt = (
        select(Feedback.id)
        .where(
            Feedback.created_by == str(user_id),
            Feedback.created_time >= threshold,
            Feedback.deleted_at.is_(None),  # 单行修复：日限应过滤软删，否则重置后仍 429
        )
        .limit(MAX_DAILY_LIMIT + 1)
    )
    result = await session.execute(stmt)
    recent = result.scalars().all()
    if len(recent) > MAX_DAILY_LIMIT:
        raise FeedbackDailyLimitError(field="daily_limit")

    now_ts = datetime.now(UTC)
    fb = Feedback(
        id=uuid4(),
        user_id=user_id,
        feedback_type=data["feedback_type"],
        text_content=data["text_content"],
        photo_url=data["photo_url"],
        body_part=data["body_part"],
        created_by=str(user_id),         # 当前操作的用户
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),
    )
    session.add(fb)
    await session.flush()

    # ACK 池（按 created_at.minute 选 seed）
    seed = now_ts.minute
    ack = pick_ack(seed=seed)
    logger.info(
        "feedback_created",
        feedback_id=str(fb.id),
        user_id=user_id,
        feedback_type=data["feedback_type"],
        body_part=data["body_part"],
    )
    # PR-2 V2 增量：响应新增 ack_text / ai_session_id / feedback_id
    # （PR-3 心情日记 + PR-5 联系客服复用；与 SPEC-A0-MASTER-IA §4 决策表一致）
    return {
        "feedback_id": str(fb.id),
        "feedback_type": data["feedback_type"],
        "body_part": data["body_part"],
        "ack": ack,
        "ack_text": ack,
        "ai_session_id": None,
        "created_at": now_ts.isoformat(),
    }


async def list_user_feedbacks(
    session: AsyncSession, *, user_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    """列出用户反馈。"""
    stmt = (
        select(Feedback)
        .where(Feedback.created_by == str(user_id))
        .order_by(Feedback.created_time.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        {
            "feedback_id": str(f.id),
            "feedback_type": f.feedback_type,
            "body_part": f.body_part,
            "text_content": f.text_content,
            "photo_url": f.photo_url,
            "created_at": f.created_time.isoformat() if f.created_time else None,
            "created_by": f.created_by,
        }
        for f in result.scalars().all()
    ]


__all__ = [
    "BODY_PARTS",
    "FEEDBACK_TYPES",
    "MAX_DAILY_LIMIT",
    "MAX_PHOTO_BYTES",
    "MAX_TEXT_LENGTH",
    "PHOTO_BODY_PARTS",
    "TEXT_ONLY_TYPES",
    "FeedbackDailyLimitError",
    "FeedbackError",
    "create_feedback",
    "list_user_feedbacks",
    "pick_ack",
    "validate_feedback",
]
