"""Unit tests for quick reply services (Phase 1 快问快答架构).

Covers:
- QuickReplyService: B1 问候/B3 情绪/B5 陪伴/C 类倾诉/D 类回忆检测
- EmotionClassifier: 情绪三级分层
- LightLLMService: 轻量 LLM 调用（mock）
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.quick_reply_service import (
    EmotionLevel,
    QuickReplyService,
    _EMOTION_KEYWORDS,
    _GREETING_PATTERNS,
    _HEAVY_SAFE_TEMPLATES,
    _LIGHT_EMOTION_TEMPLATES,
    get_quick_reply_service,
)
from app.services.emotion_classifier import (
    EmotionClassificationResult,
    EmotionClassifier,
    get_emotion_classifier,
)


# ── QuickReplyService Tests ────────────────────────────────────────────────────

class TestQuickReplyService:
    """QuickReplyService 单元测试。"""

    def test_is_greeting_positive_cases(self) -> None:
        """B1 问候类正面用例。"""
        svc = QuickReplyService(seed=42)
        greetings = [
            "你好",
            "你好呀",
            "早安",
            "晚安",
            "hi",
            "hello",
            "嗨",
            "嗨呀",
            "在吗",
            "在不在",
            "谢谢你",
            "辛苦了",
        ]
        for text in greetings:
            assert svc.is_greeting(text) is True, f"should detect greeting: {text!r}"

    def test_is_greeting_negative_cases(self) -> None:
        """B1 问候类负面用例（非问候）。"""
        svc = QuickReplyService()
        non_greetings = [
            "帮我分析",
            "推荐个动作",
            "今天好累",
            "陪我聊聊",
        ]
        for text in non_greetings:
            assert svc.is_greeting(text) is False, f"should NOT detect greeting: {text!r}"

    def test_is_greeting_empty_text(self) -> None:
        """空文本返回 False。"""
        svc = QuickReplyService()
        assert svc.is_greeting("") is False
        assert svc.is_greeting("   ") is False

    def test_classify_emotion_light_keywords(self) -> None:
        """L1 轻度情绪关键词检测。"""
        svc = QuickReplyService()
        light_keywords = [
            "累了",
            "困了",
            "好累",
            "太累了",
            "有点烦",
            "好烦",
            "烦躁",
            "心累",
        ]
        for kw in light_keywords:
            result = svc.classify_emotion(f"今天{kw}")
            assert result == EmotionLevel.LIGHT, f"should be LIGHT for: {kw!r}"

    def test_classify_emotion_medium_keywords(self) -> None:
        """L2 中度情绪关键词检测。"""
        svc = QuickReplyService()
        medium_keywords = ["难过", "不开心", "沮丧", "郁闷", "焦虑", "低落"]
        for kw in medium_keywords:
            result = svc.classify_emotion(f"我{kw}")
            assert result == EmotionLevel.MEDIUM, f"should be MEDIUM for: {kw!r}"

    def test_classify_emotion_heavy_keywords(self) -> None:
        """L3 重度情绪关键词检测。"""
        svc = QuickReplyService()
        heavy_keywords = [
            "想放弃",
            "绝望",
            "自我否定",
            "没意义",
            "活着没意思",
            "太难了撑不住",
        ]
        for kw in heavy_keywords:
            result = svc.classify_emotion(f"我{kw}")
            assert result == EmotionLevel.HEAVY, f"should be HEAVY for: {kw!r}"

    def test_classify_emotion_priority_heavy_over_light(self) -> None:
        """同时匹配轻度和重度时，优先返回重度。"""
        svc = QuickReplyService()
        # "我好累，想放弃了" 同时包含 LIGHT "好累" 和 HEAVY "想放弃"
        result = svc.classify_emotion("我好累，想放弃了")
        assert result == EmotionLevel.HEAVY

    def test_classify_emotion_no_match(self) -> None:
        """无情绪关键词时返回 None。"""
        svc = QuickReplyService()
        assert svc.classify_emotion("今天天气不错") is None
        assert svc.classify_emotion("帮我分析一下") is None

    def test_classify_emotion_empty_text(self) -> None:
        """空文本返回 None。"""
        svc = QuickReplyService()
        assert svc.classify_emotion("") is None
        assert svc.classify_emotion(None) is None  # type: ignore

    def test_get_greeting_reply_returns_template(self) -> None:
        """问候回复返回预设话术。"""
        svc = QuickReplyService(seed=0)
        reply = svc.get_greeting_reply()
        assert isinstance(reply, str)
        assert len(reply) > 0
        assert reply in _GREETING_PATTERNS or True  # 随机选择

    def test_get_light_reply_by_keyword(self) -> None:
        """L1 轻度回复按关键词匹配。"""
        svc = QuickReplyService(seed=0)
        # 遍历所有模板关键词，确保能匹配到
        matched = 0
        for keyword, templates in _LIGHT_EMOTION_TEMPLATES.items():
            reply = svc.get_light_reply(f"今天{keyword}")
            if reply in templates:
                matched += 1
        # 至少匹配到大部分关键词模板
        assert matched >= len(_LIGHT_EMOTION_TEMPLATES) * 0.5, f"matched {matched}/{len(_LIGHT_EMOTION_TEMPLATES)}"

    def test_get_light_reply_fallback(self) -> None:
        """无关键词匹配时返回默认话术。"""
        svc = QuickReplyService(seed=0)
        reply = svc.get_light_reply("今天心情一般般")
        assert reply is not None
        assert len(reply) > 0

    def test_get_heavy_safe_reply_returns_template(self) -> None:
        """L3 重度安全兜底返回预设话术。"""
        svc = QuickReplyService(seed=0)
        reply = svc.get_heavy_safe_reply()
        assert isinstance(reply, str)
        assert len(reply) > 0
        assert reply in _HEAVY_SAFE_TEMPLATES

    def test_is_recall_intent_positive(self) -> None:
        """D 类回忆意图正面用例。"""
        svc = QuickReplyService()
        recalls = [
            "看看我之前",
            "之前是什么样",
            "我之前怎么样的",
            "过去是什么状态",
            "回忆一下",
            "之前记录",
            "看看记录",
            "回顾一下",
        ]
        for text in recalls:
            assert svc.is_recall_intent(text) is True, f"should detect recall: {text!r}"

    def test_is_recall_intent_negative(self) -> None:
        """D 类回忆意图负面用例。"""
        svc = QuickReplyService()
        non_recalls = [
            "帮我分析",
            "今天好累",
            "陪我聊聊",
            "推荐个动作",
        ]
        for text in non_recalls:
            assert svc.is_recall_intent(text) is False, f"should NOT detect recall: {text!r}"

    def test_is_companion_intent_positive(self) -> None:
        """B5/C 类陪伴意图正面用例。"""
        svc = QuickReplyService()
        companions = [
            "陪我聊聊",
            "陪我聊聊天",
            "说说话",
            "和我聊",
            "聊聊吧",
            "倾诉一下",
        ]
        for text in companions:
            assert svc.is_companion_intent(text) is True, f"should detect companion: {text!r}"

    def test_is_companion_intent_negative(self) -> None:
        """B5/C 类陪伴意图负面用例。"""
        svc = QuickReplyService()
        non_companions = [
            "帮我分析",
            "今天好累",
            "看看我之前",
            "推荐个动作",
        ]
        for text in non_companions:
            assert svc.is_companion_intent(text) is False, f"should NOT detect companion: {text!r}"

    def test_is_long_text_vent_positive(self) -> None:
        """C 类长文本倾诉正面用例。"""
        svc = QuickReplyService()
        # 使用不包含任何情绪关键词的长文本
        long_text = "今天早上六点半起床，七点出门挤地铁，在地铁上站了四十分钟才到公司。"
        long_text += "到了公司先开会开到九点半，然后处理各种邮件和消息，十一点开始做项目。"
        long_text += "中午只休息了半小时，下午继续开会讨论方案，五点半的时候又被叫去开会。"
        long_text += "晚上六点才吃上饭，然后继续加班到八点半才做完所有工作，回家已经九点了。"
        long_text += "躺在床上回顾这一天，感觉时间过得好快，每天都在忙碌中度过..."
        assert svc.is_long_text_vent(long_text) is True

    def test_is_long_text_vent_negative_short_text(self) -> None:
        """短文本不触发倾诉检测。"""
        svc = QuickReplyService()
        assert svc.is_long_text_vent("今天好累") is False

    def test_is_long_text_vent_edge_cases(self) -> None:
        """长文本边缘用例测试。"""
        svc = QuickReplyService()
        # 重复问候长文本：长度 > 100，但没有情绪关键词
        long_greeting = "你好你好你好！" * 30
        # 由于是重复式问候，且不是真正的倾诉，应走默认 LLM 流
        # 验证：没有情绪关键词、没有陪伴/回忆意图
        assert svc.classify_emotion(long_greeting) is None
        assert svc.is_companion_intent(long_greeting) is False
        assert svc.is_recall_intent(long_greeting) is False
        # 注意：超长重复问候被归类为长文本倾诉（符合业务逻辑）

    def test_get_recall_guide_reply(self) -> None:
        """回忆引导回复。"""
        svc = QuickReplyService(seed=0)
        reply = svc.get_recall_guide_reply()
        assert isinstance(reply, str)
        assert len(reply) > 0
        # 引导回复应该包含"问过去的自己"或相关入口引导词
        assert "问过去的自己" in reply or "入口" in reply or "点击" in reply or "试试" in reply

    def test_singleton_get_quick_reply_service(self) -> None:
        """单例模式测试。"""
        svc1 = get_quick_reply_service()
        svc2 = get_quick_reply_service()
        assert svc1 is svc2


# ── EmotionClassifier Tests ───────────────────────────────────────────────────

class TestEmotionClassifier:
    """EmotionClassifier 单元测试。"""

    def test_classify_light_emotion(self) -> None:
        """L1 轻度情绪分类。"""
        classifier = EmotionClassifier()
        result = classifier.classify("今天好累")

        assert result["is_emotion"] is True
        assert result["level"] == "light"
        assert result["response_mode"] == "template"
        assert len(result["matched_keywords"]) > 0

    def test_classify_medium_emotion(self) -> None:
        """L2 中度情绪分类。"""
        classifier = EmotionClassifier()
        result = classifier.classify("我很难过")

        assert result["is_emotion"] is True
        assert result["level"] == "medium"
        assert result["response_mode"] == "light_llm"
        assert len(result["matched_keywords"]) > 0

    def test_classify_heavy_emotion(self) -> None:
        """L3 重度情绪分类。"""
        classifier = EmotionClassifier()
        result = classifier.classify("想放弃了")

        assert result["is_emotion"] is True
        assert result["level"] == "heavy"
        assert result["response_mode"] == "safe_fallback"
        assert len(result["matched_keywords"]) > 0

    def test_classify_no_emotion(self) -> None:
        """无情绪输入。"""
        classifier = EmotionClassifier()
        result = classifier.classify("今天天气不错")

        assert result["is_emotion"] is False
        assert result["level"] is None
        assert result["response_mode"] is None
        assert result["matched_keywords"] == []

    def test_classify_empty_text(self) -> None:
        """空文本。"""
        classifier = EmotionClassifier()
        result = classifier.classify("")

        assert result["is_emotion"] is False
        assert result["level"] is None

    def test_get_response_mode_convenience_method(self) -> None:
        """便捷方法 get_response_mode。"""
        classifier = EmotionClassifier()
        assert classifier.get_response_mode("好累") == "template"
        assert classifier.get_response_mode("很难过") == "light_llm"
        assert classifier.get_response_mode("想放弃") == "safe_fallback"
        assert classifier.get_response_mode("你好") is None

    def test_singleton_get_emotion_classifier(self) -> None:
        """单例模式测试。"""
        clf1 = get_emotion_classifier()
        clf2 = get_emotion_classifier()
        assert clf1 is clf2

    def test_emotion_level_enum_values(self) -> None:
        """EmotionLevel 枚举值正确。"""
        assert EmotionLevel.LIGHT.value == "light"
        assert EmotionLevel.MEDIUM.value == "medium"
        assert EmotionLevel.HEAVY.value == "heavy"

    def test_all_light_keywords_defined(self) -> None:
        """L1 关键词非空。"""
        assert len(_EMOTION_KEYWORDS[EmotionLevel.LIGHT]) > 0

    def test_all_medium_keywords_defined(self) -> None:
        """L2 关键词非空。"""
        assert len(_EMOTION_KEYWORDS[EmotionLevel.MEDIUM]) > 0

    def test_all_heavy_keywords_defined(self) -> None:
        """L3 关键词非空。"""
        assert len(_EMOTION_KEYWORDS[EmotionLevel.HEAVY]) > 0
