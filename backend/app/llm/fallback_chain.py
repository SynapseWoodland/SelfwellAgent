"""Deprecated compatibility wrapper for the old single fallback chain.

业务代码应显式选择：
- ``MultimodalFallbackChain``：照片智能分析
- ``TextFallbackChain``：智能管家聊天 / 调理常识

保留本模块只为迁移期兼容旧 import；默认映射到文本链，不再包含 mock 开关，
也不再混用 vision/text provider。
"""

from app.llm._base import FallbackResult
from app.llm.text_chain import TextFallbackChain

FallbackChain = TextFallbackChain

__all__ = ["FallbackChain", "FallbackResult"]
