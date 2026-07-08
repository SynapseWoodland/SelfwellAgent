"""Mock LLM Client(Sprint 0 必备)。

Sprint D 重构后**从 ``app/llm/mock_doubles.py`` 迁移到 ``tests/doubles/mock_llm.py``**,
原因:
1. 关注点分离:生产代码目录 ``app/llm/`` 不应包含测试替身
2. 业界标准:pytest / Django / Hexagonal Architecture 都把 mock 放在 ``tests/`` 下
3. mock 一旦在 ``app/`` 下,会被误 import 到生产代码,形成隐性反模式

约定:
1. 不访问任何真实 LLM endpoint(即使 api_key 已设置)
2. 通过 ``cassettes_dir`` 加载 YAML/JSON 应答;缺文件时按 schema 生成默认应答
3. 单元测试时通过 ``MockLLMClient.with_response(content=...)`` 注入确定结果
4. 业务代码**不允许** import 这个 client;只走 FastAPI ``dependency_overrides`` 注入

迁移后使用方式(``backend/tests/conftest.py``):

.. code-block:: python

    from app.llm.providers import get_multimodal_chain
    from tests.doubles.mock_llm import MockLLMClient

    app.dependency_overrides[get_multimodal_chain] = lambda: MockLLMClient()
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.llm.client import LLMClient, LLMMessage, LLMRequest, LLMResponse

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


# ─────────────────────────────────────────────────────────────────────────────
# §一 Cassette loader(VCR 风格的本地 JSON 应答)
# ─────────────────────────────────────────────────────────────────────────────
class Cassette(BaseModel):
    """单条 cassette 录制:``{request_signature: response_content}``。"""

    name: str
    requests: dict[str, str] = Field(default_factory=dict)  # key = sha256 of (messages + model)
    responses: dict[str, str] = Field(default_factory=dict)


def _default_cassettes_path() -> Path:
    """Cassette 默认目录(``backend/tests/cassettes/``)。

    Sprint D 迁移后,文件路径从 ``app/llm/_cassette_path.py`` 改成内联,
    避免跨目录的隐式依赖。``__file__ = tests/doubles/mock_llm.py``,
    ``parents[2] = backend`` 下的 ``tests/cassettes`` 路径为
    ``parents[2] / "tests" / "cassettes"`` —— 但这会指向 ``backend/tests/tests/cassettes``。

    改用 **env 变量 + 本地 backend/ 锚点**双兜底。
    """
    import os

    env_path = os.getenv("SELFWELL_CASSETTES_DIR")
    if env_path:
        return Path(env_path)
    # 兜底:相对 cwd 的 backend/tests/cassettes
    return Path.cwd() / "backend" / "tests" / "cassettes"


def _signature(req: LLMRequest) -> str:
    """生成请求签名(用于 cassette 查找 key)。

    Sprint D 重构后:``LLMRequest`` 是抽象基类,可能携带 ``images``(vision 子类)
    或不携带(text 子类)。用 ``getattr`` 兜底,确保两种请求都能生成签名。
    """
    import hashlib

    payload = json.dumps(
        {
            "messages": [m.model_dump() for m in req.messages],
            "model": req.model or "default",
            "capability": getattr(req, "capability", ""),
            "images_len": len(getattr(req, "images", []) or []),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MockLLMClient(LLMClient):
    """Mock LLM Client(Sprint 0 默认)。

    Args:
        default_response: 未命中 cassette 时默认返回内容。
        cassettes_dir: cassette 文件目录;缺则禁用。
        latency_ms: 模拟网络延迟(毫秒)。

    """

    provider_name = "mock"

    def __init__(
        self,
        *,
        default_response: str = "(Mock LLM 应答:未命中 cassette)",
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
        """测试 helper:固定下一次 ``achat`` 返回。"""
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
        """Test helper:将 (request, response) 写入 cassette dict(不落盘)。"""
        sig = _signature(request)
        self._cassettes[sig] = response
        return sig

    async def ainvoke(self, messages: list[BaseMessage], **kwargs: Any) -> BaseMessage:
        """LangChain 兼容接口(``init_chat_model`` 调用)。

        将 LangChain ``BaseMessage`` 列表转为内部 ``TextRequest`` 并走 ``achat``。

        LangChain 的 ``message.type`` 命名跟 OpenAI 不一致:
        ``HumanMessage.type == "human"`` / ``AIMessage.type == "ai"`` /
        ``SystemMessage.type == "system"``。需要映射到
        ``LLMMessage.role`` 的 ``"user" / "assistant" / "system"``,
        否则 Pydantic ``Literal["system", "user", "assistant"]`` 校验失败。
        """
        from langchain_core.messages import AIMessage

        from app.llm.client import TextRequest

        role_map = {"human": "user", "ai": "assistant", "system": "system"}
        llm_messages = [
            LLMMessage(role=role_map.get(m.type, "user"), content=m.content)
            for m in messages
        ]
        request = TextRequest(messages=llm_messages)
        resp = await self.achat(request)
        return AIMessage(content=resp.content)


# Alias 方便迁移期兼容(老的 `from app.llm.mock_doubles import MockDoubles` 可继续工作到 Sprint E)
MockDoubles = MockLLMClient

__all__ = ["Cassette", "MockDoubles", "MockLLMClient"]