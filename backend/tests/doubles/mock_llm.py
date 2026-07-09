"""Mock LLM Client for tests.

通过 monkeypatch ``app.llm`` 中的 ``text_llm`` / ``multimodal_llm`` 来注入 mock。
不依赖已删除的 LLMClient / LLMResponse / budget / providers 等。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage


# ─────────────────────────────────────────────────────────────────────────────
# §一 Cassette loader (VCR 风格的本地 JSON 应答)
# ─────────────────────────────────────────────────────────────────────────────


def _default_cassettes_path() -> Path:
    """Cassette 默认目录 (``backend/tests/cassettes/``)。"""
    import os

    env_path = os.getenv("SELFWELL_CASSETTES_DIR")
    if env_path:
        return Path(env_path)
    return Path.cwd() / "backend" / "tests" / "cassettes"


def _signature(messages: list[dict[str, Any]]) -> str:
    """生成请求签名（用于 cassette 查找 key）。"""
    import hashlib

    payload = json.dumps(
        {"messages": messages, "capability": ""},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Cassette:
    """单条 cassette 录制：``{request_signature: response_content}``。"""

    def __init__(self) -> None:
        self.requests: dict[str, str] = {}
        self.responses: dict[str, str] = {}


# ─────────────────────────────────────────────────────────────────────────────
# §二 MockLLM — LangChain ainvoke 兼容接口
# ─────────────────────────────────────────────────────────────────────────────


class MockLLM:
    """Mock LLM，支持 cassette + default_response。

    使用方式（monkeypatch）：
        from tests.doubles.mock_llm import MockLLM
        import app.llm
        app.llm.text_llm = MockLLM(default_response="hello")
        app.llm.multimodal_llm = MockLLM(default_response='{"directions":[],"tags":[],"summary":""}')
    """

    provider_name = "mock"

    def __init__(
        self,
        *,
        default_response: str = "(Mock LLM 应答)",
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

    def with_response(self, content: str) -> "MockLLM":
        """测试 helper：固定下一次 ``ainvoke`` 返回。"""
        self._default_response = content
        return self

    async def ainvoke(self, messages: list[Any], **kwargs: Any) -> AIMessage:
        """LangChain 兼容接口。"""
        await asyncio.sleep(self._latency_ms / 1000.0)
        # 从 langchain_core.messages 提取文本
        msg_contents = [m.content for m in messages if hasattr(m, "content")]
        sig = _signature([{"content": c} for c in msg_contents])
        content = self._cassettes.get(sig, self._default_response)
        return AIMessage(content=content)

    # ── 兼容旧 alias ─────────────────────────────────────────────────────────
    async def achat(self, messages: list[Any]) -> AIMessage:
        return await self.ainvoke(messages)

    def record(self, messages: list[Any], response: str) -> str:
        """Test helper：将 (request, response) 写入 cassette dict（不落盘）。"""
        msg_contents = [m.content for m in messages if hasattr(m, "content")]
        sig = _signature([{"content": c} for c in msg_contents])
        self._cassettes[sig] = response
        return sig


# 兼容旧 alias
MockDoubles = MockLLM

__all__ = ["Cassette", "MockDoubles", "MockLLM"]
