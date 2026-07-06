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
    """Auto-apply @pytest.mark.load to all tests in backend/tests/load/."""
    for item in items:
        if "load" in item.fspath and item.fspath.strpath.endswith("_load"):
            item.add_marker(pytest.mark.load)
