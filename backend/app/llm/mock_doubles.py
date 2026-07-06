"""Mock LLM Client（Sprint 0 必备）。

真源：coding-standards SKILL.md §十二"Mock LLM 用 unittest.mock.AsyncMock，禁止调用真实模型"

约定：
1. 不访问任何真实 LLM endpoint（即使 api_key 已设置）
2. 通过 ``cassettes_dir`` 加载 YAML/JSON 应答；缺文件时按 schema 生成默认应答
3. 单元测试时通过 ``MockLLMClient.with_response(content=...)`` 注入确定结果
4. 任何业务代码除非明确 sprint 任务，都必须 import 这个 client
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.llm.client import LLMClient, LLMRequest, LLMResponse

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


# ─────────────────────────────────────────────────────────────────────────────
# §一 Cassette loader（VCR 风格的本地 JSON 应答）
# ─────────────────────────────────────────────────────────────────────────────
class Cassette(BaseModel):
    """单条 cassette 录制：``{request_signature: response_content}``。"""

    name: str
    requests: dict[str, str] = Field(default_factory=dict)  # key = sha256 of (messages + model)
    responses: dict[str, str] = Field(default_factory=dict)


def _default_cassettes_path() -> Path:
    """Cassette 默认目录（``backend/tests/cassettes/``）。"""
    from app.llm._cassette_path import default_cassettes_path

    return default_cassettes_path()


def _signature(req: LLMRequest) -> str:
    """生成请求签名（用于 cassette 查找 key）。"""
    import hashlib

    payload = json.dumps(
        {
            "messages": [m.model_dump() for m in req.messages],
            "model": req.model or "default",
            "images_len": len(req.images),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MockLLMClient(LLMClient):
    """Mock LLM Client（Sprint 0 默认）。

    Args:
        default_response: 未命中 cassette 时默认返回内容。
        cassettes_dir: cassette 文件目录；缺则禁用。

    """

    provider_name = "mock"

    def __init__(
        self,
        *,
        default_response: str = "（Mock LLM 应答：未命中 cassette）",
        cassettes_dir: Path | None = None,
        latency_ms: int = 50,
    ) -> None:
        self._default_response = default_response
        self._latency_ms = latency_ms
        self._cassettes: dict[str, str] = {}
        self.cassettes_dir = cassettes_dir or _default_cassettes_path()
        self._load_cassettes()

    def _load_cassettes(self) -> None:
        """从 ``cassettes_dir`` 加载 ``*.json`` 录制。"""
        if not self.cassettes_dir.exists():
            return
        for path in self.cassettes_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for sig, content in data.items():
                    self._cassettes[sig] = content
            except (json.JSONDecodeError, OSError):
                continue

    def with_response(self, content: str) -> MockLLMClient:
        """测试 helper：固定下一次 ``achat`` 返回。"""
        self._default_response = content
        return self

    async def achat(self, request: LLMRequest) -> LLMResponse:
        await asyncio.sleep(self._latency_ms / 1000.0)
        sig = _signature(request)
        content = self._cassettes.get(sig, self._default_response)
        return LLMResponse(
            content=content,
            model=request.model or self.provider_name,
            latency_ms=self._latency_ms,
            token_count=len(content),
            cost_yuan=0.0,
            finish_reason="stop",
            raw={"mock": True, "signature": sig},
        )

    def record(self, request: LLMRequest, response: str) -> str:
        """Test helper：将 (request, response) 写入 cassette dict（不落盘）。"""
        sig = _signature(request)
        self._cassettes[sig] = response
        return sig

    async def ainvoke(self, messages: "list[BaseMessage]", **kwargs: Any) -> "BaseMessage":
        """LangChain 兼容接口（Sprint 2+ ``init_chat_model`` 调用）。

        将 LangChain ``BaseMessage`` 列表转为内部 ``LLMRequest`` 并走 ``achat``。
        """
        from langchain_core.messages import AIMessage

        llm_messages = [
            LLMMessage(role=m.type, content=m.content) for m in messages
        ]
        request = LLMRequest(messages=llm_messages)
        resp = await self.achat(request)
        return AIMessage(content=resp.content)


# Alias 方便迁移期兼容
MockDoubles = MockLLMClient

__all__ = ["Cassette", "MockDoubles", "MockLLMClient"]
