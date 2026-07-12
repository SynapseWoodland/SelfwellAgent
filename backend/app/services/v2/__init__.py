"""app.services.v2 — V2 IA PR-2 服务聚合。

包含 5 个 service（IA V2.2 §2A.2 + §2A.3）：
- badge_service（勋章体系读写）
- album_service（时光相册照片 + 统计）
- archive_service（21 天小档案聚合）
- notification_service（通知偏好）
- support_service（FAQ + 数据导出 + 账号注销）

新 service 仅做轻量 re-export，避免外层 import 路径过长。
"""

from __future__ import annotations

from app.services.v2.album_service import (
    AlbumError,
    AlbumWeekFormatError,
    get_album_stats,
    list_album_photos_by_week,
)
from app.services.v2.archive_service import (
    ArchiveError,
    get_archive_summary,
)
from app.services.v2.badge_service import (
    BadgeCodeError,
    BadgeError,
    BadgeProgressError,
    get_badges_summary,
    increment_progress,
    list_user_badges,
    unlock_badge,
)
from app.services.v2.notification_service import (
    DEFAULT_PREF_VALUES,
    NotificationPrefError,
    list_notification_prefs,
    seed_default_prefs,
    update_notification_prefs,
)
from app.services.v2.support_service import (
    COOL_DOWN_DAYS,
    FAQ_LIST,
    DeletionAlreadyPendingError,
    SupportError,
    cancel_deletion,
    list_faq,
    request_account_deletion,
    request_data_export,
)

__all__ = [
    "COOL_DOWN_DAYS",
    "DEFAULT_PREF_VALUES",
    "FAQ_LIST",
    "AlbumError",
    "AlbumWeekFormatError",
    "ArchiveError",
    "BadgeCodeError",
    "BadgeError",
    "BadgeProgressError",
    "DataExportLimitError",
    "DeletionAlreadyPendingError",
    "DeletionNotFoundError",
    "NotificationPrefError",
    "SupportError",
    "cancel_deletion",
    "get_album_stats",
    "get_archive_summary",
    "get_badges_summary",
    "increment_progress",
    "list_album_photos_by_week",
    "list_faq",
    "list_notification_prefs",
    "list_user_badges",
    "request_account_deletion",
    "request_data_export",
    "seed_default_prefs",
    "unlock_badge",
]
