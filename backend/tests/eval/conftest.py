"""Pytest 配置：让 ``backend.tests.intercept.*`` 能 ``from app...`` 导入合规检查器。

pyproject.toml 未声明 rootdir，pytest 默认从 ``tests`` 父目录（backend）开始
向根寻找 ``pyproject.toml``，因此 ``app`` 包的导入路径可直接使用，无需 sys.path
前置；本 conftest 仅做防御性兜底（避免根目录变更后失效）。
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))