"""Pytest configuration for load tests.

Provides fixtures and markers for running Locust-based load tests
alongside the project's other test suites.
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for load testing."""
    config.addinivalue_line(
        "markers",
        "load: marks tests as load/performance tests (deselect with '-m \"not load\"')",
    )
    config.addinivalue_line(
        "markers",
        "locust: marks tests that invoke Locust programmatically",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply @pytest.mark.load to all tests in backend/tests/load/.

    V5.2.1-PR0.x: pytest 9.x removed ``item.fspath`` (LocalPath); migrated to
    ``item.path`` (pathlib.Path). We coerce to ``str`` for the same substring
    semantics as the pre-9.x implementation.
    """
    for item in items:
        # pytest 9.x: item.fspath 移除，改用 item.path（pathlib.Path）
        path_str = str(item.path)
        if "load" in path_str and path_str.endswith("_load"):
            item.add_marker(pytest.mark.load)
