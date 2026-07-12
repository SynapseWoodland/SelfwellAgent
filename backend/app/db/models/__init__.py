"""app.db.models — 14 张业务表 ORM（Sprint 0 + V2 IA PR-2 增量）。

真源：``docs/spec/facts-anchor.md`` §2 + ``db/init/01-schema.sql`` +
``docs/data/data-dictionary.md``（字段定义）+ ``plans/v2-unified-parent.md`` §2.2（V2 4 表）。

约定：1 个表 = 1 个文件，统一 ``__tablename__`` 显式声明 + 完整 ``Mapped[...]`` 注解。

PR-2（V2 IA）增量：
- ``AccountDeletionRequest``（account_deletion_requests · §2A.2.3）
- ``UserBadge``（user_badges · §2A.2.1）
- ``UserNotificationPref``（user_notification_prefs · §2A.2.2）
- ``UserSelfTag``（user_self_tags · §2A.2.4）

实现注意：所有 ORM 在此处 import 后，调用 ``configure_mappers()`` 一次完成关系配对
（避免 ``User.feedbacks`` 在使用 ``User(...)`` 时反向找不到 ``feedbacks`` 报错）。
"""

from sqlalchemy.orm import configure_mappers

from app.db.models.account_deletion_request import AccountDeletionRequest
from app.db.models.ai_messages import AIMessage
from app.db.models.ai_sessions import AISession
from app.db.models.checkin import Checkin
from app.db.models.feedback import Feedback
from app.db.models.plan import Plan
from app.db.models.post import Post
from app.db.models.recall_sessions import RecallSession
from app.db.models.report import Report
from app.db.models.user import User
from app.db.models.user_badge import UserBadge
from app.db.models.user_notification_pref import UserNotificationPref
from app.db.models.user_self_tag import UserSelfTag
from app.db.models.video import Video

# 显式触发 mapper 配置，让 User↔Feedback、AIMessage↔Feedback 等反向关系即刻生效
configure_mappers()

__all__ = [
    "AIMessage",
    "AISession",
    "AccountDeletionRequest",
    "Checkin",
    "Feedback",
    "Plan",
    "Post",
    "RecallSession",
    "Report",
    "User",
    "UserBadge",
    "UserNotificationPref",
    "UserSelfTag",
    "Video",
]