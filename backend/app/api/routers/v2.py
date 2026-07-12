"""V2 IA PR-2 router.

真源：``plans/v2-unified-parent.md`` §2.2 + IA V2.2 §2A.3。

本模块不含 prefix；mount 在 ``main.py`` 用 ``app.include_router(v2_router, prefix="/api/v1")``，
最终路径即 spec 要求的 ``/api/v1/{users/me/badges,me/album/...,me/archive/...}``。

9 接口契约（路径已锁定）：
| # | Method | URI | 责任 |
|---|--------|-----|------|
| 1 | GET | ``/api/v1/users/me/badges`` | 用户勋章列表（已解锁 + 在路上） |
| 2 | GET | ``/api/v1/me/album/photos?week=YYYY-WNN`` | 按周取相册照片 |
| 3 | GET | ``/api/v1/me/album/stats`` | 相册聚合统计 |
| 4 | GET | ``/api/v1/me/archive/summary`` | 21 天小档案 |
| 5 | GET | ``/api/v1/me/notification-settings`` | 读取通知偏好 |
| 6 | PUT | ``/api/v1/me/notification-settings`` | 批量更新通知偏好 |
| 7 | GET | ``/api/v1/support/faq`` | FAQ 列表 |
| 8 | POST | ``/api/v1/me/data-export`` | 数据导出（异步 job_id） |
| 9 | POST | ``/api/v1/me/account-deletion`` | 注销请求（7 天冷静期） |

3 接口扩展（现有路由）：
- POST /api/v1/feedback：响应加 ack_text / ai_session_id / feedback_id
- POST /api/v1/butler/recall：body 加 days_offset
- GET /api/v1/users/me：响应加 badges_summary / streak_days
（已在 users_v1.py / feedback_service.py / butler_v1.py / profile_service.py 完成）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.v2.album_service import (
    AlbumError,
    AlbumWeekFormatError,
    get_album_stats,
    list_album_photos_by_week,
)
from app.services.v2.archive_service import ArchiveError, get_archive_summary
from app.services.v2.badge_service import (
    BadgeError,
    list_user_badges,
)
from app.services.v2.notification_service import (
    NotificationPrefError,
    list_notification_prefs,
    seed_default_prefs,
    update_notification_prefs,
)
from app.services.v2.support_service import (
    DeletionAlreadyPendingError,
    SupportError,
    list_faq,
    request_account_deletion,
    request_data_export,
)
from app.services.v2.support_service import (
    cancel_deletion as cancel_deletion_service,
)

# ════════════════════════════════════════════════════════════════════════════════
# §一 APIRouter
# ════════════════════════════════════════════════════════════════════════════════
# 用 prefix 聚合 4 个子 prefix；mount 在 main.py 用 /api/v1
v2_router = APIRouter(tags=["v2"])


# ───────────────────────────────────────────────────────────────────────────────
# Pydantic Models（响应 + 请求 schema）
# ───────────────────────────────────────────────────────────────────────────────
class DataResponse(BaseModel):
    code: int = 0
    data: dict


class NotificationPrefsUpdate(BaseModel):
    """通知偏好批量更新（PUT）。"""

    prefs: dict[str, dict]


class CancelDeletionRequest(BaseModel):
    """取消注销（PR-5 前端用，PR-2 提供 endpoint 方便测试与运维）。"""

    deletion_id: str


# ───────────────────────────────────────────────────────────────────────────────
# §1 GET /users/me/badges
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.get("/users/me/badges", summary="[V2] 用户勋章列表")
async def get_user_badges_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    try:
        return {"code": 0, "data": await list_user_badges(session, user_id=user_id)}
    except BadgeError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc


# ───────────────────────────────────────────────────────────────────────────────
# §2 GET /me/album/photos?week=YYYY-WNN
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.get("/me/album/photos", summary="[V2] 按周取相册照片")
async def get_album_photos_endpoint(
    week: str = Query(..., description="ISO 周，格式 YYYY-WNN"),
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    try:
        return {
            "code": 0,
            "data": await list_album_photos_by_week(
                session, user_id=user_id, week=week
            ),
        }
    except AlbumWeekFormatError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    except AlbumError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc


# ───────────────────────────────────────────────────────────────────────────────
# §3 GET /me/album/stats
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.get("/me/album/stats", summary="[V2] 相册聚合统计")
async def get_album_stats_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    return {"code": 0, "data": await get_album_stats(session, user_id=user_id)}


# ───────────────────────────────────────────────────────────────────────────────
# §4 GET /me/archive/summary
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.get("/me/archive/summary", summary="[V2] 21 天小档案")
async def get_archive_summary_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    try:
        return {
            "code": 0,
            "data": await get_archive_summary(session, user_id=user_id),
        }
    except ArchiveError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc


# ───────────────────────────────────────────────────────────────────────────────
# §5 GET /me/notification-settings
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.get("/me/notification-settings", summary="[V2] 读取通知偏好")
async def get_notification_settings_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    # 首次访问时填入默认 pref
    await seed_default_prefs(session, user_id=user_id)
    return {
        "code": 0,
        "data": await list_notification_prefs(session, user_id=user_id),
    }


# ───────────────────────────────────────────────────────────────────────────────
# §6 PUT /me/notification-settings
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.put("/me/notification-settings", summary="[V2] 批量更新通知偏好")
async def put_notification_settings_endpoint(
    body: NotificationPrefsUpdate,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    try:
        return {
            "code": 0,
            "data": await update_notification_prefs(
                session, user_id=user_id, prefs=body.prefs
            ),
        }
    except NotificationPrefError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc


# ───────────────────────────────────────────────────────────────────────────────
# §7 GET /support/faq
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.get("/support/faq", summary="[V2] FAQ 列表")
async def get_faq_endpoint(
    category: str | None = Query(default=None, description="按 category 过滤"),
) -> dict:
    return {"code": 0, "data": list_faq(category=category)}


# ───────────────────────────────────────────────────────────────────────────────
# §8 POST /me/data-export
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.post("/me/data-export", summary="[V2] 数据导出（异步 job_id）")
async def post_data_export_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    return {
        "code": 0,
        "data": await request_data_export(session, user_id=user_id),
    }


# ───────────────────────────────────────────────────────────────────────────────
# §9 POST /me/account-deletion
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.post("/me/account-deletion", summary="[V2] 启动账号注销（7 天冷静期）")
async def post_account_deletion_endpoint(
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    try:
        return {
            "code": 0,
            "data": await request_account_deletion(session, user_id=user_id),
        }
    except DeletionAlreadyPendingError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc


# ───────────────────────────────────────────────────────────────────────────────
# 辅助端点（PR-2 不计入 9 主接口；给 PR-5 前端 + 测试用）
# ───────────────────────────────────────────────────────────────────────────────
@v2_router.post("/me/account-deletion/cancel", summary="[V2] 取消注销请求")
async def cancel_account_deletion_endpoint(
    body: CancelDeletionRequest,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),  # noqa: B008
) -> dict:
    try:
        return {
            "code": 0,
            "data": await cancel_deletion_service(
                session, user_id=user_id, deletion_id=body.deletion_id
            ),
        }
    except SupportError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc


__all__ = [
    "CancelDeletionRequest",
    "DataResponse",
    "NotificationPrefsUpdate",
    "v2_router",
]
