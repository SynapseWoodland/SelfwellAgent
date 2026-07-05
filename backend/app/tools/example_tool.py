"""示例 BaseTool（占位 · Sprint 0）。

真源：coding-standards SKILL.md §八"tools/ 继承 BaseTool，统一 retry/fallback"。

⚠ Sprint 0 仅签名样例；Sprint 2+ M2/M3/M5 业务工具替换。
"""

from __future__ import annotations

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class ExampleToolArgs(BaseModel):
    """示例工具入参。"""

    query: str = Field(..., description="待执行的查询语句")


class ExampleTool(BaseTool):
    """示例工具 —— 仅 echo 输入。"""

    name: str = "example_tool"
    description: str = "Echo the input query (placeholder tool)."
    args_schema: type[BaseModel] = ExampleToolArgs

    def _run(self, query: str) -> str:
        return f"echo: {query}"

    async def _arun(self, query: str) -> str:
        return f"echo: {query}"


__all__ = ["ExampleTool", "ExampleToolArgs"]
