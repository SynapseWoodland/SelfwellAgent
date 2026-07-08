"""多模态 LLM 降级链，专用于照片智能分析。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config
from app.core.log import logger
from app.llm._base import BaseFallbackChain, FallbackResult
from app.llm.client import LLMRequest, MultimodalRequest


class MultimodalFallbackChain(BaseFallbackChain):
    """多模态降级链：Doubao Seedream → Qwen VL → 规则引擎。"""

    capability = "vision"

    def __init__(
        self,
        *,
        on_all_failed: Callable[[LLMRequest | str], str] | None = None,
    ) -> None:
        self._on_all_failed = on_all_failed or _default_multimodal_fallback
        super().__init__()

    def _build_clients(self) -> Sequence[Any]:
        cfg = app_config.llm
        specs = [
            {
                "provider": "primary_multimodal",
                "model": cfg.multi_model,
                "base_url": cfg.multi_base_url,
                "api_key": cfg.multi_api_key,
            },
            {
                "provider": "backup_multimodal",
                "model": cfg.backup_multi_model,
                "base_url": cfg.multi_base_url,
                "api_key": cfg.backup_multi_api_key,
            },
        ]
        clients: list[Any] = []
        for spec in specs:
            if not spec["api_key"] or not spec["base_url"]:
                logger.warning(
                    "multimodal_chain_provider_skipped",
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
                    "multimodal_chain_provider_init_failed",
                    provider=spec["provider"],
                    model=spec["model"],
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:200],
                )
        return clients

    def _fallback(self, request: LLMRequest | str, *, attempts: int) -> FallbackResult:
        return FallbackResult(
            content=self._on_all_failed(request),
            provider_used="rule-engine",
            attempts=attempts,
            cost_yuan=0.0,
        )


def _default_multimodal_fallback(request: LLMRequest | str) -> str:
    return "（规则引擎兜底：今日 AI 服务繁忙，请稍后重试）"


def is_multimodal_request(request: LLMRequest | str) -> bool:
    """判断请求是否需要 vision 模型。"""
    return isinstance(request, MultimodalRequest) or (
        isinstance(request, LLMRequest) and request.capability == "vision"
    )


__all__ = ["MultimodalFallbackChain", "is_multimodal_request"]
