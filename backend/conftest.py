"""Pytest 全局配置：注入 `backend/` 到 sys.path。

测试文件位于 ``backend/tests/{intercept,eval}/``,需要绝对包导入
``backend.services.compliance.*``,因此将 ``backend/`` 加入 sys.path。

为何用 ``backend/`` 而不是 ``services/``：保持与 ``python -m backend.eval.runner``
入口一致（runner 自身也注入 ``backend/``）。
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


# 兼容 shim:``backend.services.*`` 重定向到 ``app.services.*``（pre-Sprint 0 旧布局）
# ``tests/intercept/test_*.py`` 仍用 ``from backend.services.compliance.checker import ...``
def _install_backend_services_alias() -> None:
    """Lazy import app.services, then mount backend.services as alias package."""
    try:
        # 触发 app.services 加载
        import app.services
        import app.services.compliance
        import app.services.compliance.checker  # noqa: F401
    except ImportError:
        return

    _compat = types.ModuleType("backend")
    _compat.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("backend", _compat)

    _app_services_mod = sys.modules["app.services"]
    _backend_services = types.ModuleType("backend.services")
    _backend_services.__path__ = _app_services_mod.__path__  # type: ignore[attr-defined]
    sys.modules["backend.services"] = _backend_services

    for _name in ("compliance",):
        _full_app = f"app.services.{_name}"
        _sub = sys.modules.get(_full_app)
        if _sub is None:
            continue
        _backend_sub_name = f"backend.services.{_name}"
        _backend_sub = types.ModuleType(_backend_sub_name)
        _backend_sub.__path__ = _sub.__path__  # type: ignore[attr-defined]
        sys.modules[_backend_sub_name] = _backend_sub
        _check = sys.modules.get(f"{_full_app}.checker")
        if _check is not None:
            _backend_sub.checker = _check
            sys.modules[f"{_backend_sub_name}.checker"] = _check


_install_backend_services_alias()
