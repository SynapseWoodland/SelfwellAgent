"""测试 fixtures（Sprint 0）：test_engine / mock_llm_client / fake_redis。

⚠ Sprint 0 仅签名骨架；真接入 Sprint 2+。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture
def test_engine() -> AsyncEngine | None:
    """异步 SQLite 内存引擎（默认 None；测试按需覆盖）。"""
    return None


@pytest.fixture
def mock_llm_client() -> object:
    """Mock LLM client fixture。"""
    from tests.doubles.mock_llm import MockLLMClient

    return MockLLMClient(default_response="(test fixture response)")


@pytest.fixture
def fake_redis() -> object:
    """Fake Redis fixture（Sprint 0 占位）。"""

    class _Fake:
        def __init__(self) -> None:
            self._store: dict[str, str] = {}

        async def get(self, key: str) -> str | None:
            return self._store.get(key)

        async def set(self, key: str, value: str, ex: int | None = None) -> None:
            self._store[key] = value

        async def incr(self, key: str) -> int:
            self._store[key] = str(int(self._store.get(key, "0")) + 1)
            return int(self._store[key])

        async def aclose(self) -> None:
            self._store.clear()

    return _Fake()


@pytest.fixture
async def async_sessionmaker(test_engine: AsyncEngine | None) -> AsyncIterator[object | None]:
    """Sessionmaker fixture（与 mock LLM 同 shape；Sprint 2+ 用真实 engine）。"""
    yield None
