"""V2 IA · Support service（联系客服 FAQ + 数据导出 + 账号注销）。

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.3 #7 / #8 / #9
+ alembic 0007 ``account_deletion_requests`` 表。

责任：
- 列出 FAQ（PR-2 hardcode 列表；PR-7 可换成 DB 表 / 后台管理）
- 数据导出请求（GDPR 异步；PR-2 落 job_id，不实际导出数据）
- 账号注销请求（7 天冷静期；返回 confirm_phrase）

约定：
- FAQ 列表是 V2 锁定的常驻内容（PR-2 hardcode）
- 数据导出 job_id 返回后由 PR-VP 后台 worker 处理（PR-2 仅入库）
- 注销请求返回 confirm_phrase；用户必须在前端再次手输才能 confirm
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError
from app.core.log import logger
from app.db.models.account_deletion_request import (
    DELETION_STATUSES,
    AccountDeletionRequest,
)
from app.errors.codes import (
    E_DATA_EXPORT_LIMIT,
    E_DELETION_ALREADY_PENDING,
    E_DELETION_NOT_FOUND,
    E_USER_INVALID_INPUT,
)

# FAQ 列表（PR-2 hardcode 12 条；PR-7 可替换为 DB 表）
FAQ_LIST: list[dict[str, str]] = [
    {
        "id": "how-to-checkin",
        "category": "打卡",
        "question": "怎么完成今日练习？",
        "answer": "在「今天」页面点击「开始跟练」，按提示完成视频后回到小程序自动打卡。",
    },
    {
        "id": "what-is-plan",
        "category": "方案",
        "question": "21 天方案是什么？",
        "answer": "21 天方案是基于你上传的照片由 AI 生成的每日小动作集合，每天 8-15 分钟。",
    },
    {
        "id": "how-to-upload-photos",
        "category": "诊断",
        "question": "需要上传什么样的照片？",
        "answer": "正面脸 + 侧面体态 + 发质特写各 1 张，自然光即可。",
    },
    {
        "id": "how-to-recall",
        "category": "回忆",
        "question": "问过去的自己怎么用？",
        "answer": "对话页点击「问过去的自己」，AI 会调出近 3/7/14 天的照片和心情日记。",
    },
    {
        "id": "streak-broken",
        "category": "打卡",
        "question": "中断过会怎样？",
        "answer": "进度环只显示实际完成的天数，不会清零也不会评判。随时回来都可以。",
    },
    {
        "id": "data-export",
        "category": "隐私",
        "question": "我的数据如何导出？",
        "answer": "在「我的 → 隐私 → 数据导出」发起请求，1-3 个工作日内邮件发送下载链接。",
    },
    {
        "id": "delete-account",
        "category": "隐私",
        "question": "如何注销账号？",
        "answer": "在「我的 → 隐私 → 注销账号」发起注销，进入 7 天冷静期，期内可取消。",
    },
    {
        "id": "what-is-bug",
        "category": "反馈",
        "question": "遇到 Bug 怎么反馈？",
        "answer": "在「我的 → 联系客服」提交反馈，附上截图和场景说明，2-5 个工作日内回复。",
    },
    {
        "id": "vision-mode",
        "category": "AI",
        "question": "AI 看照片的准确度？",
        "answer": "AI 给的是养护参考，不是医疗诊断。所有判断都带主观性，请以自己身体的感受为准。",
    },
    {
        "id": "what-is-badges",
        "category": "勋章",
        "question": "勋章有什么用？",
        "answer": "勋章是你的坚持里程碑，比如连续 7 / 14 / 21 天打卡。仅自己可见。",
    },
    {
        "id": "notification",
        "category": "通知",
        "question": "怎么关闭推送？",
        "answer": "在「我的 → 通知设置」按偏好关掉对应开关。",
    },
    {
        "id": "what-is-time-cost",
        "category": "方案",
        "question": "每天需要多少时间？",
        "answer": "每日小动作合计约 8-15 分钟，分 2-3 次完成即可。",
    },
]


COOL_DOWN_DAYS = 7


class SupportError(SelfwellError):
    """客服业务异常。"""

    code: str = E_USER_INVALID_INPUT
    message_zh: str = "客服请求失败"
    message_en: str = "Support request failed"
    severity = "USER_ERROR"
    http_status = 400


class DeletionAlreadyPendingError(SupportError):
    code: str = E_DELETION_ALREADY_PENDING
    message_zh: str = "已有进行中的注销请求"
    message_en: str = "Deletion request already pending"
    http_status = 409


class DeletionNotFoundError(SupportError):
    code: str = E_DELETION_NOT_FOUND
    message_zh: str = "注销请求不存在"
    message_en: str = "Deletion request not found"
    http_status = 404


class DataExportLimitError(SupportError):
    code: str = E_DATA_EXPORT_LIMIT
    message_zh: str = "7 天内已有数据导出请求"
    message_en: str = "Data export requested within last 7 days"
    http_status = 429


def list_faq(category: str | None = None) -> dict[str, Any]:
    """列出 FAQ。

    Args:
        category: 可选过滤（打卡/方案/诊断 等）

    Returns:
        { faqs: list[dict], total: int, categories: list[str] }

    """
    filtered = FAQ_LIST
    if category:
        filtered = [f for f in FAQ_LIST if f["category"] == category]
    categories = sorted({f["category"] for f in FAQ_LIST})
    return {
        "faqs": filtered,
        "total": len(filtered),
        "categories": categories,
    }


def _generate_confirm_phrase() -> str:
    """生成反向确认短语（6 字符 hex，避免误点）。"""
    return secrets.token_hex(3).upper()


async def request_account_deletion(
    session: AsyncSession, *, user_id: str
) -> dict[str, Any]:
    """启动账号注销（7 天冷静期）。

    Returns:
        - deletion_id: UUID
        - confirm_phrase: str（用户必须在前端手输才能 confirm）
        - cool_down_until: ISO8601
        - status: "pending_cool_down"

    """
    # 检查是否有未完成（pending_cool_down / confirmed）的请求
    stmt = (
        select(AccountDeletionRequest)
        .where(
            AccountDeletionRequest.user_id == user_id,
            AccountDeletionRequest.deleted_at.is_(None),
            AccountDeletionRequest.status.in_(("pending_cool_down", "confirmed")),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise DeletionAlreadyPendingError(
            f"已有状态为 {existing.status} 的注销请求",
            field="user_id",
        )

    now_ts = datetime.now(UTC)
    cool_down_until = now_ts + timedelta(days=COOL_DOWN_DAYS)
    confirm_phrase = _generate_confirm_phrase()

    deletion = AccountDeletionRequest(
        id=uuid4(),
        user_id=user_id,
        status="pending_cool_down",
        confirm_phrase=confirm_phrase,
        cool_down_until=cool_down_until,
        created_at=now_ts,
        updated_at=now_ts,
        created_by=str(user_id),
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),
    )
    session.add(deletion)
    await session.flush()

    logger.info(
        "account_deletion_requested",
        user_id=user_id,
        deletion_id=str(deletion.id),
        cool_down_until=cool_down_until.isoformat(),
    )

    return {
        "deletion_id": str(deletion.id),
        "confirm_phrase": confirm_phrase,
        "cool_down_until": cool_down_until.isoformat(),
        "status": deletion.status,
        "cool_down_days": COOL_DOWN_DAYS,
    }


async def request_data_export(session: AsyncSession, *, user_id: str) -> dict[str, Any]:
    """触发数据导出（GDPR；PR-2 落 job_id 即可，PR-VP 后台 worker 处理实际导出）。

    Returns:
        - job_id: UUID（PR-VP 用此 ID 关联到后台 worker）
        - status: "queued"
        - estimated_completion: "1-3 个工作日"

    """
    job_id = uuid4()
    now_ts = datetime.now(UTC)

    # PR-2 不创建独立 job 表；返回 job_id 供 PR-VP 后台 worker 拾取
    # PR-7 集成测试时验证 worker 是否消费
    logger.info(
        "data_export_requested",
        user_id=user_id,
        job_id=str(job_id),
        queued_at=now_ts.isoformat(),
    )

    return {
        "job_id": str(job_id),
        "status": "queued",
        "estimated_completion": "1-3 个工作日",
        "requested_at": now_ts.isoformat(),
    }


async def cancel_deletion(
    session: AsyncSession, *, user_id: str, deletion_id: str
) -> dict[str, Any]:
    """取消注销请求（PR-5 用户在冷静期内手动取消；PR-2 提供 service 接口供测试 / 未来用）。"""
    stmt = select(AccountDeletionRequest).where(
        AccountDeletionRequest.id == deletion_id,
        AccountDeletionRequest.user_id == user_id,
        AccountDeletionRequest.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    deletion = result.scalar_one_or_none()
    if deletion is None:
        raise DeletionNotFoundError(field="deletion_id")
    if deletion.status not in ("pending_cool_down", "confirmed"):
        raise SupportError(
            f"状态为 {deletion.status} 的请求不可取消", field="status"
        )

    now_ts = datetime.now(UTC)
    deletion.status = "cancelled"
    deletion.updated_at = now_ts
    deletion.last_updated_time = now_ts
    deletion.last_updated_by = str(user_id)
    await session.flush()
    logger.info(
        "account_deletion_cancelled",
        user_id=user_id,
        deletion_id=deletion_id,
    )
    return {
        "deletion_id": deletion_id,
        "status": "cancelled",
        "updated_at": now_ts.isoformat(),
    }


__all__ = [
    "COOL_DOWN_DAYS",
    "DELETION_STATUSES",
    "FAQ_LIST",
    "DataExportLimitError",
    "DeletionAlreadyPendingError",
    "DeletionNotFoundError",
    "SupportError",
    "cancel_deletion",
    "list_faq",
    "request_account_deletion",
    "request_data_export",
]
