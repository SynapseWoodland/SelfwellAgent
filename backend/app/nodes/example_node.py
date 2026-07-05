"""示例节点（占位 · Sprint 0）。

真源：coding-standards SKILL.md §六"节点签名 ``async def node(state, runtime) -> dict``，
禁止修改 state，必须返回状态增量"。

⚠ Sprint 0 仅签名样例；Sprint 1+ 由业务模块替换。
"""

from __future__ import annotations

from typing import Any

from app.core.log import logger
from app.state.types import AgentContext, AgentState

# Sprint 0 stub：Runtime 在 langgraph 0.5+ 才稳定；Sprint 1 替换为真实 import。
Runtime: Any = Any


async def example_node(
    state: AgentState,
    runtime: Any,
) -> dict[str, object]:
    """占位节点 —— 仅写入 history；不修改 state。

    Returns:
        状态增量 ``dict``（注入到 LangGraph reducer）。

    """
    logger.info("example_node_invoke")
    _ = (runtime, AgentContext)  # 满足接口；runtime 内可读 trace_id / user_id
    return {
        "history": [{"event": "example_node_invoked", "query": state.get("query", "")}],
        "error": None,
    }


__all__ = ["Runtime", "example_node"]
