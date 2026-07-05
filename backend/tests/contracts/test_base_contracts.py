"""Contract smoke test — 验证 NodeInput / NodeOutput ``extra='forbid'`` 行为。"""

from __future__ import annotations

from pydantic import ValidationError


def test_node_input_extra_forbidden() -> None:
    """``extra='forbid'`` 生效：额外字段抛 ValidationError。"""
    from app.contracts.common import NodeInput, NodeOutput

    class _I(NodeInput):
        q: str

    class _O(NodeOutput):
        r: str

    _I(q="hi")  # OK
    _O(r="ok")  # OK
    import pytest

    with pytest.raises(ValidationError):
        _I(q="hi", bogus="nope")  # type: ignore[call-arg]


def test_example_contracts_importable() -> None:
    from app.contracts.example import ExampleInput, ExampleOutput

    out = ExampleOutput(results=["x"], error=None)
    assert out.results == ["x"]
    ExampleInput(query="hi", options=["a", "b"])
