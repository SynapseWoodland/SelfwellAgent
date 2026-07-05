"""State smoke test — ``AgentState`` TypedDict 顶层 key 与 reducer 行为。"""

from __future__ import annotations

import typing


def test_agent_state_top_level_keys() -> None:
    """``AgentState`` 顶层 key 必须 ≥ 5；error 必须存在。"""
    from app.state.types import AgentState

    expected_required = {"query", "messages", "history", "error"}
    hints = typing.get_type_hints(AgentState, include_extras=True)
    for key in expected_required:
        assert key in hints, f"AgentState 缺少顶层 key {key}"


def test_agent_state_messages_reducer_is_add() -> None:
    """``messages`` 字段带 ``operator.add`` reducer。

    TypedDict 把 ``Annotated[...]`` 编码为 string ForwardRef；必须走
    ``typing.get_type_hints(include_extras=True)`` 才能解析。
    """
    from app.state.types import AgentState

    hints = typing.get_type_hints(AgentState, include_extras=True)
    ann = hints["messages"]
    assert hasattr(ann, "__metadata__"), "messages 必须 Annotated[...] 装饰"
    import operator

    assert operator.add in ann.__metadata__, "messages reducer 必须是 operator.add"


def test_agent_context_has_trace_and_user_id() -> None:
    from app.state.types import AgentContext

    hints = typing.get_type_hints(AgentContext, include_extras=True)
    assert "trace_id" in hints
    assert "user_id" in hints
