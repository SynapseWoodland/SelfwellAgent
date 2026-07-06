"""FastAPI dependencies（认证 / DB session / 公共 header 解析）。

集中管理所有 Depends() 工厂；routers 严禁直接 import session / 解析 token。
"""

from app.api import deps

__all__ = ["deps"]
