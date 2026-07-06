"""app.db.models — 10 张业务表 ORM（Sprint 0）。

真源：``docs/spec/facts-anchor.md`` §2 + ``db/init/01-schema.sql`` +
``docs/data/data-dictionary.md``（字段定义）。

约定：1 个表 = 1 个文件，统一 ``__tablename__`` 显式声明 + 完整 ``Mapped[...]`` 注解。
"""

from app.db.models.ai_messages import AIMessage
from app.db.models.ai_sessions import AISession
from app.db.models.checkin import Checkin
from app.db.models.feedback import Feedback
from app.db.models.plan import Plan
from app.db.models.post import Post
from app.db.models.recall_sessions import RecallSession
from app.db.models.report import Report
from app.db.models.user import User
from app.db.models.video import Video

__all__ = [
    "AIMessage",
    "AISession",
    "Checkin",
    "Feedback",
    "Plan",
    "Post",
    "RecallSession",
    "Report",
    "User",
    "Video",
]
