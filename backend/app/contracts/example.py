"""示例契约（占位 · Sprint 0）。

说明：此文件由 Sprint 1+ 真业务节点替换；当前仅作为 contracts/ 目录骨架样例。
"""

from __future__ import annotations

from pydantic import Field

from app.contracts.common import NodeInput, NodeOutput


class ExampleInput(NodeInput):
    """示例入参。"""

    query: str
    options: list[str] = Field(default_factory=list)


class ExampleOutput(NodeOutput):
    """示例出参。"""

    results: list[str] = Field(default_factory=list)
    error: str | None = None


__all__ = ["ExampleInput", "ExampleOutput"]
