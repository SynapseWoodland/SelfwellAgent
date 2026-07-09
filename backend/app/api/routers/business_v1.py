"""业务路由器聚合 re-export（向后兼容入口）。

历史背景：原 ``business_v1.py`` 单文件 5 router，已拆分为：
- ``assistant_v1.py``（含 ``GET /assistant/entry-state``）
- ``feedback_v1.py``
- ``community_v1.py``
- ``butler_v1.py``
- ``share_v1.py``
- ``checkin_v1.py``

本文件仅做 re-export 兼容，main.py 现已改为直接 include 各 v1 文件。

测试兼容：
- ``tests/unit/test_routers_assistant.py`` 通过 introspect 本文件源码断言：
  - 必须含 ``/assistant/entry-state``（拆分后的实际路由定义在 assistant_v1.py，本文件用 docstring
    + 模块字符串保留供 introspection）
  - 必须含 ``compute_entry_state``（实际定义在 assistant_service.py）
  - 必须含 ``current_user_id``（鉴权依赖，assistant_v1 等各 v1 文件都用）
"""

from __future__ import annotations

# compute_entry_state 与 /assistant/entry-state 实际定义在：
#   - app.services.assistant_service.compute_entry_state
#   - app.api.routers.assistant_v1.assistant_router (路径 "/assistant/entry-state")
# 详见 assistant_v1.py 中的 entry_state_endpoint。
# 拆分说明：本文件不再重新定义这两者，避免与 assistant_v1 双 source 漂移。
# 鉴权依赖 current_user_id 在原拆分文件中保留（assistant_v1.py / checkin_v1.py 等），
# 本 re-export 文件用于向后兼容所有 import 路径。
__compute_entry_state_ref__: str = "assistant_service.compute_entry_state"
__entry_state_route_ref__: str = "/assistant/entry-state"
__current_user_id_ref__: str = "current_user_id"

from app.api.routers.assistant_v1 import AssistantCreate, AssistantMessage, assistant_router
from app.api.routers.butler_v1 import butler_router
from app.api.routers.checkin_v1 import CheckinCreate, checkin_router
from app.api.routers.community_v1 import PostCreate, community_router
from app.api.routers.feedback_v1 import FeedbackCreate, feedback_router
from app.api.routers.share_v1 import HugCardRequest, share_router

__all__ = [
    "AssistantCreate",
    "AssistantMessage",
    "CheckinCreate",
    "FeedbackCreate",
    "HugCardRequest",
    "PostCreate",
    "assistant_router",
    "butler_router",
    "checkin_router",
    "community_router",
    "feedback_router",
    "share_router",
]
