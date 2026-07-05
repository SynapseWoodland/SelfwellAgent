"""节点契约基类（Sprint 0 骨架）。

真源：coding-standards SKILL.md §七"contracts/ 继承 NodeInput/NodeOutput"。

约定：
- 每个节点对应 ``contracts/`` 内一对 Input/Output（Pydantic v2）
- ``extra='forbid'`` 禁止额外字段（避免静默兼容错误）
- 业务模块按 ``contracts/<module>.py`` 命名
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NodeInput(BaseModel):
    """节点入参基类。"""

    model_config = ConfigDict(extra="forbid", frozen=True)


class NodeOutput(BaseModel):
    """节点出参基类。"""

    model_config = ConfigDict(extra="forbid", frozen=True)


__all__ = ["NodeInput", "NodeOutput"]
