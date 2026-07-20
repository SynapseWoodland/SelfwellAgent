"""Smoke test — verify Sprint 0 base app structure imports cleanly.

Sprint 0 阶段要求 ``uv run pytest tests -q`` 0 errors。
"""

from __future__ import annotations


def test_sprint0_app_imports() -> None:
    """App 顶层包与 Sprint 0 落地的核心模块均可 import。"""
    import app
    import app.agents
    import app.api
    import app.api.middleware
    import app.auth
    import app.conf
    import app.conf.app_config
    import app.contracts
    import app.core
    import app.core.errors
    import app.core.log
    import app.core.retry
    import app.core.trace
    import app.db
    import app.errors
    import app.errors.codes
    import app.llm
    import app.nodes
    import app.notification
    import app.prompts
    import app.rules
    import app.state
    import app.storage
    import app.tools  # noqa: F401


def test_error_severity_constants() -> None:
    """ErrorSeverity 4 级常量可直接 ``from app.core.errors import TRANSIENT``。"""
    from app.core.errors import (
        DEGRADED,
        PERMANENT,
        TRANSIENT,
        USER_ERROR,
        ErrorSeverity,
    )

    assert PERMANENT == "PERMANENT"
    assert TRANSIENT == "TRANSIENT"
    assert USER_ERROR == "USER_ERROR"
    assert DEGRADED == "DEGRADED"
    literal: ErrorSeverity = TRANSIENT
    assert literal in {"PERMANENT", "TRANSIENT", "USER_ERROR", "DEGRADED"}


def test_codes_module_loads() -> None:
    """``app.errors.codes`` 含 ≥ 80 个 ``E_*`` 常量。"""
    from app.errors import codes

    constants = [getattr(codes, n) for n in dir(codes) if n.startswith("E_")]
    min_required = 80
    assert len(constants) >= min_required, (
        f"仅 {len(constants)} 条 E_*，未达 docs/architecture/error-codes.md 字典完整性门槛"
    )
