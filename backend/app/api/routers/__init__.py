"""app.api.routers — FastAPI 路由命名空间（Sprint 1+）。

真源：``docs/api/openapi.yaml``（所有路径 / 请求体 / 响应体以 openapi 为契约）。

Sprint 1 PR-1 落地：
- ``system.py``：仅含 ``GET /healthz``（Sprint 1 PR-1 唯一业务路由）

后续 PR 会增量加入：
- ``v1/auth.py``（PR-2 微信登录）
- ``v1/users.py``（PR-2 用户档案）
- ``v1/diagnosis.py``（PR-3 多模态诊断）
- ``v1/plans.py`` / ``v1/videos.py``（PR-4 21 天方案）
- ...等
"""