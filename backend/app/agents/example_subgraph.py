"""示例 LangGraph 子图（占位 · Sprint 0）。

真源：coding-standards SKILL.md §一"agents/ 仅图编排，业务逻辑抽离到 nodes/tools"。

⚠ Sprint 0 仅签名样例；Sprint 2+ 由 M2/M3/M5 等业务子图替换。
"""

from __future__ import annotations

from app.nodes.example_node import example_node


def build_example_subgraph() -> object:
    """构造 ``StateGraph`` 骨架 —— Sprint 0 仅返回字符串占位，避免拉入 langgraph。

    真实实施在 Sprint 2+，届时替换为：
        >>> from langgraph.graph import StateGraph, START, END
        >>> g = StateGraph(AgentState)
        >>> g.add_node("example", example_node)
        >>> g.add_edge(START, "example")
        >>> g.add_edge("example", END)
        >>> return g.compile()
    """
    _ = example_node  # 满足 ruff F401；真实接入时显式调用
    return "example_subgraph_placeholder"


__all__ = ["build_example_subgraph"]
