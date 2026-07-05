"""Subgraph smoke test — ``build_example_subgraph`` 占位返回可被消费。"""

from __future__ import annotations


def test_example_subgraph_placeholder() -> None:
    """Sprint 0 占位子图必须不抛错 + 返回可识别的对象。"""
    from app.agents.example_subgraph import build_example_subgraph

    g = build_example_subgraph()
    assert g is not None
