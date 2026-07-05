"""Placeholder node smoke test — ``example_node`` 返回状态增量 dict。"""

from __future__ import annotations

import asyncio


def test_example_node_returns_state_delta() -> None:
    """节点返回值必须是 dict 增量（禁止修改 state）。"""
    from app.nodes.example_node import example_node

    state: dict[str, object] = {
        "query": "hello",
        "messages": [],
        "history": [],
        "error": None,
        "retry_count": 0,
    }

    async def run() -> dict[str, object]:
        return await example_node(state, runtime=object())  # type: ignore[arg-type]

    delta = asyncio.run(run())
    assert "history" in delta
    assert "error" in delta
    assert delta["error"] is None
    assert isinstance(delta["history"], list)
    assert len(delta["history"]) == 1
    entry = delta["history"][0]
    assert isinstance(entry, dict)
    assert entry.get("event") == "example_node_invoked"
