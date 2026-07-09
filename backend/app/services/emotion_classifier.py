"""情绪分类服务：统一入口（基于 quick_reply_service）。

对外暴露统一接口，返回分类结果 dict。
"""

from __future__ import annotations

from typing import TypedDict

from app.services.quick_reply_service import (
    EmotionLevel,
    QuickReplyService,
    get_quick_reply_service,
)


class EmotionClassificationResult(TypedDict):
    """情绪分类结果。"""

    is_emotion: bool
    level: str | None
    response_mode: str | None
    matched_keywords: list[str]


_RESPONSE_MODE_MAP: dict[EmotionLevel, str] = {
    EmotionLevel.LIGHT: "template",
    EmotionLevel.MEDIUM: "light_llm",
    EmotionLevel.HEAVY: "safe_fallback",
}


class EmotionClassifier:
    """情绪分类服务。

    封装 QuickReplyService，提供统一的情绪分类接口。
    """

    def __init__(self, service: QuickReplyService | None = None) -> None:
        """初始化情绪分类器。

        Args:
            service: 可选，指定 QuickReplyService 实例。

        """
        self._service = service or get_quick_reply_service()

    def classify(self, text: str) -> EmotionClassificationResult:
        """分类用户输入的情绪强度。

        Args:
            text: 用户输入文本。

        Returns:
            EmotionClassificationResult

        """
        level = self._service.classify_emotion(text)

        if level is None:
            return {
                "is_emotion": False,
                "level": None,
                "response_mode": None,
                "matched_keywords": [],
            }

        from app.services.quick_reply_service import _EMOTION_KEYWORDS

        matched_keywords: list[str] = []
        keywords = _EMOTION_KEYWORDS.get(level, ())
        for keyword in keywords:
            if keyword in text:
                matched_keywords.append(keyword)

        return {
            "is_emotion": True,
            "level": level.value,
            "response_mode": _RESPONSE_MODE_MAP.get(level),
            "matched_keywords": matched_keywords,
        }

    def get_response_mode(self, text: str) -> str | None:
        """获取响应模式（便捷方法）。

        Args:
            text: 用户输入文本。

        Returns:
            响应模式字符串或 None。

        """
        result = self.classify(text)
        return result["response_mode"]


# ── 单例导出 ─────────────────────────────────────────────────────────────────

_emotion_classifier: EmotionClassifier | None = None


def get_emotion_classifier() -> EmotionClassifier:
    """获取 EmotionClassifier 单例。"""
    global _emotion_classifier
    if _emotion_classifier is None:
        _emotion_classifier = EmotionClassifier()
    return _emotion_classifier


__all__ = [
    "EmotionClassificationResult",
    "EmotionClassifier",
    "get_emotion_classifier",
]
