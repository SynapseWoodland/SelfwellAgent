"""文本 LLM 降级链，专用于智能管家聊天与调理常识。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config
from app.core.log import logger
from app.llm._base import BaseFallbackChain, FallbackResult
from app.llm.client import LLMRequest


class TextFallbackChain(BaseFallbackChain):
    """文本降级链：GLM → DeepSeek → 静态文案。"""

    capability = "text"

    def __init__(
        self,
        *,
        on_all_failed: Callable[[LLMRequest | str], str] | None = None,
    ) -> None:
        self._on_all_failed = on_all_failed or _default_text_fallback
        super().__init__()

    def _build_clients(self) -> Sequence[Any]:
        cfg = app_config.llm
        specs = [
            {
                "provider": "primary_text",
                "model": cfg.model,
                "base_url": cfg.base_url,
                "api_key": cfg.api_key,
            },
            {
                "provider": "backup_text",
                "model": cfg.backup_model,
                "base_url": cfg.backup_base_url,
                "api_key": cfg.backup_api_key,
            },
        ]
        clients: list[Any] = []
        for spec in specs:
            if not spec["api_key"] or not spec["base_url"]:
                logger.warning(
                    "text_chain_provider_skipped",
                    provider=spec["provider"],
                    model=spec["model"],
                    reason="missing_api_key_or_base_url",
                )
                continue
            try:
                clients.append(
                    init_chat_model(
                        model=spec["model"],
                        model_provider="openai",
                        base_url=spec["base_url"],
                        api_key=spec["api_key"],
                        temperature=cfg.temperature,
                        max_tokens=cfg.max_tokens,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "text_chain_provider_init_failed",
                    provider=spec["provider"],
                    model=spec["model"],
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:200],
                )
        return clients

    def _fallback(self, request: LLMRequest | str, *, attempts: int) -> FallbackResult:
        return FallbackResult(
            content=self._on_all_failed(request),
            provider_used="static-fallback",
            attempts=attempts,
            cost_yuan=0.0,
        )


def _default_text_fallback(request: LLMRequest | str) -> str:
    return "（AI 服务繁忙，请稍后再试）"


__all__ = ["TextFallbackChain"]
