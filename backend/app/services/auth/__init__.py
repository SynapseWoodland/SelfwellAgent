"""M1 auth services（jargon 拆分）。

真源：``docs/spec/SPEC-M1-wechat-login.md`` V1.1
+ ``docs/api/openapi.yaml`` ``#/components/schemas/WxLogin*``。

约定：
- 业务规则只在本包内实现（不写进 routers）
- 不在 agents/ 内做编排
- 仅暴露 service 函数 + 异常
"""

from app.services.auth import jwt_service, phone_login_service, wx_login_service

__all__ = ["jwt_service", "phone_login_service", "wx_login_service"]
