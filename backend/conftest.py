"""Pytest 全局配置：注入 `backend/` 到 sys.path。

测试文件位于 ``backend/tests/{intercept,eval}/``,需要绝对包导入
``backend.services.compliance.*``,因此将 ``backend/`` 加入 sys.path。

为何用 ``backend/`` 而不是 ``services/``：保持与 ``python -m backend.eval.runner``
入口一致（runner 自身也注入 ``backend/``）。
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))