"""LLM Structured Output schemas（与 SemanticMind contracts 风格一致）。

用于 ``with_structured_output()`` 的 Pydantic 模型。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DiagnosisDirection(BaseModel):
    """单条改善方向。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="方向标题，如「肩颈放松」")
    description: str = Field(..., description="详细描述，包含具体动作或建议")
    video_id: str | None = Field(default=None, description="关联视频 ID，无则 null")


class DiagnosisOutput(BaseModel):
    """多模态诊断输出 schema。"""

    model_config = ConfigDict(extra="forbid")

    directions: list[DiagnosisDirection] = Field(
        ..., description="3-5 条改善方向", min_length=1
    )
    tags: list[str] = Field(..., description="7-14 个标签词", min_length=1)
    summary: str = Field(..., description="50-100 字整体总结")


__all__ = ["DiagnosisDirection", "DiagnosisOutput"]
