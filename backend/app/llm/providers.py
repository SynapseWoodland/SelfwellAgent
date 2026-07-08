"""LLM chain 的 FastAPI dependency provider。

Sprint D 重构后,LLM chain 通过 ``Depends(get_multimodal_chain)`` 注入,
测试通过 ``fastapi_app.dependency_overrides[get_multimodal_chain] = ...`` 替换为 mock。

生产代码只暴露真实 chain；测试替换整条 provider，不在业务构造函数里放测试开关。
"""

from __future__ import annotations

from app.llm.multimodal_chain import MultimodalFallbackChain
from app.llm.text_chain import TextFallbackChain


def get_multimodal_chain() -> MultimodalFallbackChain:
    """生产 provider:返回真实的 ``MultimodalFallbackChain``。

    测试通过 ``app.dependency_overrides[get_multimodal_chain] = lambda: MockChain()`` 替换。
    """
    return MultimodalFallbackChain()


def get_text_chain() -> TextFallbackChain:
    """生产 provider:返回真实的 ``TextFallbackChain``。"""
    return TextFallbackChain()


__all__ = ["get_multimodal_chain", "get_text_chain"]
