"""TraceContextMiddleware（re-export from app.core.trace for symmetry）。

真源：``app.core.trace.TraceContextMiddleware``；本模块位于
``app/api/middleware/trace.py``，仅做 thin re-export，便于按 plan §3.1 目录树对齐。
"""

from __future__ import annotations

from app.core.trace import TraceContextMiddleware

__all__ = ["TraceContextMiddleware"]
