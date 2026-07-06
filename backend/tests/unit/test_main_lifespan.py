"""Unit test — lifespan 启动期调用 setup_logging（PR-1 AC-5）。

实现真源：``backend/app/main.py`` lifespan 上下文管理器。
"""

from __future__ import annotations

from typing import Callable
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.conf.app_config import app_config


class _SpyState:
    """Spy state for setup_logging 调用记录。"""

    __slots__ = ("count", "level")

    def __init__(self) -> None:
        self.count: int = 0
        self.level: str | None = None


def _make_setup_spy() -> tuple[_SpyState, Callable[..., None]]:
    """构造 setup_logging spy。"""
    captured = _SpyState()

    def _spy(*, level: str = "INFO", json_sink: bool = True) -> None:
        captured.count += 1
        captured.level = level

    return captured, _spy


def test_lifespan_calls_setup_logging() -> None:
    """AC-5: 后端 lifespan 启动期必须调用 setup_logging。"""
    from app.main import app

    captured, _spy = _make_setup_spy()
    with patch("app.main.setup_logging", side_effect=_spy), TestClient(app):
        pass

    assert captured.count >= 1, (
        f"setup_logging 在 lifespan 启动期未被调用（count={captured.count}）"
    )
    assert captured.level is not None


def test_lifespan_uses_app_config_log_level() -> None:
    """AC-5: 传递给 setup_logging 的 level 必须来自 app_config.log_level。"""
    from app.main import app

    captured, _spy = _make_setup_spy()
    with patch("app.main.setup_logging", side_effect=_spy), TestClient(app):
        pass

    assert captured.count >= 1
    assert captured.level == app_config.log_level, (
        f"setup_logging level={captured.level}，app_config.log_level={app_config.log_level}"
    )


def test_lifespan_is_asynccontextmanager() -> None:
    """Lifespan 必须可被 FastAPI lifespan= 接受（即是 async contextmanager）。"""
    from app.main import lifespan

    # @asynccontextmanager 装饰后 lifespan 是函数，但调用后返回 AsyncContextManager
    cm = lifespan(None)
    assert hasattr(cm, "__aenter__")
    assert hasattr(cm, "__aexit__")


def test_lifespan_idempotent_on_setup_logging() -> None:
    """连续两次 TestClient 上下文，app 应仍可 boot（setup_logging 内部幂等）。"""
    from app.main import app

    with TestClient(app):
        pass
    with TestClient(app):
        pass
    # 仅断言不抛异常
    assert True
