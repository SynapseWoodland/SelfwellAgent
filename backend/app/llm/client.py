"""LLM 4 级降级链 Client（Sprint 0 骨架）。

真源：``docs/spec/facts-anchor.md`` §9 + ADR-0003。

约定：
1. **Sprint 0 一律使用 MockLLMClient**（``mock_doubles.MockLLMClient``），不调真实模型
2. 真实模型必须在 Sprint 2+ 通过降级链 + tenacity retry 接入
3. input/output schema 严格 Pydantic v2（``LLMRequest`` / ``LLMResponse``）
4. 任何 LLM 调用必须带 ``trace_id`` / ``request_id`` / ``user_id_pseudo`` 上下文
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# §一 Pydantic v2 Schema（跨 4 级降级链统一入参 / 出参）
# ─────────────────────────────────────────────────────────────────────────────
class LLMMessage(BaseModel):
    """单条聊天消息。"""

    role: str = Field(..., description="user / assistant / system")
    content: str = Field(..., min_length=0, max_length=4000)


class LLMRequest(BaseModel):
    """LLM 统一入参。"""

    messages: list[LLMMessage] = Field(default_factory=list)
    images: list[str] = Field(
        default_factory=list,
        description="Image URLs or base64 (for multimodal diagnosis / vision tasks)",
    )
    model: str | None = Field(default=None, description="Override default model")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """LLM 统一出参。"""

    content: str
    model: str
    latency_ms: int
    token_count: int = 0
    cost_yuan: float = 0.0
    finish_reason: str = "stop"
    raw: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# §二 LLMClient 抽象基类
# ─────────────────────────────────────────────────────────────────────────────
class LLMClient(ABC):
    """LLM 客户端抽象基类。

    所有 4 个 impl（Claude / GPT-4o / Qwen VL / DeepSeek-VL）必须继承并实现：
    - :meth:`provider_name` — 降级链 trace 用
    - :meth:`chat` — 同步入口（local stub 用，仅在 ``mock_doubles.MockLLMClient`` 重写为 AsyncMock）
    - :meth:`achat` — 异步入口
    """

    provider_name: str = "abstract"

    @abstractmethod
    async def achat(self, request: LLMRequest) -> LLMResponse:
        """异步 chat 调用。"""

    async def health_check(self) -> bool:
        """默认健康检查：能被调通即 True；子类可重写为 ping endpoint。"""
        return True


# ─────────────────────────────────────────────────────────────────────────────
# §三 4 impl（占位，enabled=False；Sprint 2+ 真接入时打开）
# ─────────────────────────────────────────────────────────────────────────────
class ClaudeClient(LLMClient):
    """Claude Sonnet 4（主，1 级）。Sprint 0 仅占位。"""

    provider_name = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514") -> None:
        self._api_key = api_key
        self._model = model

    async def achat(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("Sprint 2+ 接入真实 Claude API；Sprint 0 用 MockLLMClient")


class GPT4oClient(LLMClient):
    """GPT-4o（备 1，2 级）。Sprint 0 仅占位。"""

    provider_name = "gpt-4o"

    def __init__(self, api_key: str = "", model: str = "gpt-4o") -> None:
        self._api_key = api_key
        self._model = model

    async def achat(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("Sprint 2+ 接入真实 OpenAI API；Sprint 0 用 MockLLMClient")


class QwenVLClient(LLMClient):
    """Qwen VL（备 2，3 级）。Sprint 0 仅占位。"""

    provider_name = "qwen-vl-max"

    def __init__(self, api_key: str = "", model: str = "qwen-vl-max") -> None:
        self._api_key = api_key
        self._model = model

    async def achat(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("Sprint 2+ 接入真实 DashScope API；Sprint 0 用 MockLLMClient")


class DeepSeekVLClient(LLMClient):
    """DeepSeek-VL（备 3，4 级）。Sprint 0 仅占位。"""

    provider_name = "deepseek-vl"

    def __init__(
        self,
        api_key: str = "",
        model: str = "deepseek-vl",
        base_url: str = "https://api.deepseek.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    async def achat(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("Sprint 2+ 接入真实 DeepSeek HTTP API；Sprint 0 用 MockLLMClient")


__all__ = [
    "ClaudeClient",
    "DeepSeekVLClient",
    "GPT4oClient",
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "QwenVLClient",
]
