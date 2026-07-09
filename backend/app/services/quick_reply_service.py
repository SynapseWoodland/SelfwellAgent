"""快问快答服务：检测 + 分层响应（PRD §3.5.3 MVP 输入框能力边界）。

B 类快问分类体系：
- B1 问候类：早安/你好/hi/hello/嗨 → 预设话术 + 打字机
- B3 情绪类：累了/难过/沮丧 → 三级分层（L1/L2/L3）
- B5 陪伴类：陪我聊聊/说说话 → 轻量 LLM
- C 类：长文本倾诉 → 轻量 LLM
- D 类：主动回忆 → 引导回忆入口
"""

from __future__ import annotations

import random
import re
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class EmotionLevel(Enum):
    """情绪强度枚举（三级分层）。"""

    LIGHT = "light"  # 轻度：累了/困了/有点烦
    MEDIUM = "medium"  # 中度：难过/不开心/沮丧
    HEAVY = "heavy"  # 重度：想放弃/绝望/自我否定


# B1 问候类正则模式
_GREETING_PATTERNS: tuple[str, ...] = (
    r"^早安$",
    r"^晚安$",
    r"^你好[呀啊]?$",
    r"^嗨[呀啊]?$",
    r"^(hi|hello|hey)[!,。]?$",
    r"谢谢你|感谢你|辛苦了",
    r"吃了吗|睡得(好|怎么样)|心情如何",
    r"在吗|在不在",
    r"^好$|^[Dd]ay$",
    r"^(你好[呀啊]?)+$",
    r"^(嗨[呀啊]?)+$",
    r"^(hi|hello|hey)[!,。]*$",
)

_GREETING_KEYWORDS: tuple[str, ...] = (
    "你好",
    "您好",
    "早安",
    "晚安",
    "嗨",
    "hi",
    "hello",
    "hey",
    "在吗",
    "在不在",
)

# B1 问候类预设话术
_GREETING_TEMPLATES: tuple[str, ...] = (
    "今天又迈出了一步，真的很棒！",
    "你好！有什么我可以帮你的吗？",
    "早上好，记得给自己一个微笑 😊",
    "嗨，又见面啦~",
    "在呢，慢慢说，我在听。",
    "晚上好，今天辛苦了。",
)

# B3 情绪类关键词映射
_EMOTION_KEYWORDS: dict[EmotionLevel, tuple[str, ...]] = {
    EmotionLevel.LIGHT: (
        "累了",
        "困了",
        "有点烦",
        "好累",
        "太累了",
        "困",
        "睡不着",
        "睡不好",
        "没精神",
        "好困",
        "好烦",
        "烦躁",
        "心累",
    ),
    EmotionLevel.MEDIUM: (
        "难过",
        "不开心",
        "沮丧",
        "郁闷",
        "焦虑",
        "烦闷",
        "低落",
        "消沉",
        "灰心",
        "气馁",
        "失落",
        "委屈",
    ),
    EmotionLevel.HEAVY: (
        "想放弃",
        "绝望",
        "自我否定",
        "没意义",
        "活着没意思",
        "不如死了",
        "讨厌自己",
        "恨自己",
        "太难了撑不住",
        "没救了",
        "彻底完了",
        "活着好累",
    ),
}

# L1 轻度情绪预设话术（按关键词映射）
_LIGHT_EMOTION_TEMPLATES: dict[str, tuple[str, ...]] = {
    "累了": (
        "休息一下也没关系，我陪你。",
        "累了就歇一会儿，你已经做得很好了。",
        "给自己放个小假吧~",
    ),
    "困了": (
        "给自己泡杯茶，休息一会儿吧。",
        "困了就去休息，不要硬撑哦。",
        "先休息一下，精神好再继续。",
    ),
    "有点烦": (
        "深呼吸，慢慢来。",
        "先停一停，别太着急。",
        "深呼吸，我在这里陪着你。",
    ),
    "好累": (
        "辛苦了，先休息一下吧。",
        "累了就歇一会儿，你已经很努力了。",
        "给自己一点恢复的时间~",
    ),
    "太累了": (
        "辛苦了，好好休息一下吧。",
        "放松一下，你已经很棒了。",
        "休息一下再继续也不迟~",
    ),
    "睡不着": (
        "试试深呼吸，放松一下~",
        "睡前做几个深呼吸会好很多。",
        "放松心情，不要给自己太大压力。",
    ),
    "睡不好": (
        "睡眠很重要，记得好好休息。",
        "睡前少看手机，会好睡一些~",
        "愿你今晚能睡个好觉。",
    ),
    "没精神": (
        "精神不好的时候，允许自己休息。",
        "没精神就歇一歇，不要勉强自己。",
        "给自己充充电吧~",
    ),
    "好困": (
        "先睡一会儿吧，别硬撑。",
        "困了就休息，身体最重要。",
        "去休息吧，晚安~",
    ),
    "好烦": (
        "深呼吸，慢慢来。",
        "先冷静一下，我在这里。",
        "别着急，先放松一下~",
    ),
    "烦躁": (
        "深呼吸，让自己平静下来。",
        "烦躁的时候，试试慢慢吐气。",
        "我在这里陪你~",
    ),
    "心累": (
        "心累的时候，就让自己休息一下吧。",
        "你已经付出很多了，给自己一些温柔。",
        "好好休息，你已经很努力了。",
    ),
}

# L1 默认话术
_LIGHT_DEFAULT_TEMPLATES: tuple[str, ...] = (
    "休息一下也没关系，我陪你。",
    "深呼吸，慢慢来~",
    "先停一停，别太着急。",
    "给自己一点恢复的时间吧。",
)

# L3 重度情绪安全兜底话术
_HEAVY_SAFE_TEMPLATES: tuple[str, ...] = (
    "放弃很容易，但你走到这里已经很棒了。要不要休息一下再继续？",
    "听起来你现在很难受。我在这里陪着你。",
    "你已经很努力了，每个小小的进步都值得被看见。",
    "我知道现在很难，但你不是一个人。我在这里。",
    "给自己一点时间，你已经做得很好了。",
)

# D 类回忆意图关键词
_RECALL_INTENT_PATTERNS: tuple[str, ...] = (
    r"看看我(之前|以前)",
    r"(之前|过去)(是什么|是怎么|什么样|怎么样)",
    r"我之前(怎么|什么样|怎么样)",
    r"过去是什么(状态|情况)",
    r"回忆一下",
    r"之前记录",
    r"看看记录",
    r"回顾一下",
)

# B5/C 类陪伴意图关键词
_COMPANION_INTENT_PATTERNS: tuple[str, ...] = (
    r"陪我聊(天|聊)",
    r"说说话",
    r"和我聊",
    r"聊聊(吧|吗)",
    r"随便聊",
    r"说会儿",
    r"谈谈心",
    r"倾诉",
)


class QuickReplyService:
    """快问服务：检测 + 分层响应。

    根据 PRD §3.5.3 MVP 输入框能力边界，实现 B 类快问分层路由。
    """

    def __init__(self, *, seed: int | None = None) -> None:
        """初始化快问服务。

        Args:
            seed: 可选的随机种子，用于测试复现。

        """
        self._greeting_patterns = [_compile_pattern(p) for p in _GREETING_PATTERNS]
        self._recall_patterns = [_compile_pattern(p) for p in _RECALL_INTENT_PATTERNS]
        self._companion_patterns = [_compile_pattern(p) for p in _COMPANION_INTENT_PATTERNS]
        self._seed = seed

    def _random_choice[T](self, seq: tuple[T, ...]) -> T:
        """从序列中随机选择一项。"""
        if self._seed is not None:
            rng = random.Random(self._seed)  # noqa: S311 — cosmetic test seeding
            return rng.choice(seq)
        return random.choice(seq)  # noqa: S311 — cosmetic copy selection

    def is_greeting(self, text: str) -> bool:
        """检测 B1 问候类。"""
        if not text:
            return False
        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # 1. 正则模式匹配
        for pattern in self._greeting_patterns:
            if pattern.search(text_lower) or pattern.search(text_stripped):
                return True

        # 2. 问候关键词宽松匹配
        for kw in _GREETING_KEYWORDS:
            if text_stripped.startswith(kw):
                rest = text_stripped[len(kw):]
                if len(rest) <= len(kw) * 5:
                    punct_set = set("！？!?.，, ")
                    greeting_chars = set(kw)
                    if all(c in punct_set or c in greeting_chars for c in rest):
                        return True

        return False

    def classify_emotion(self, text: str) -> EmotionLevel | None:
        """检测 B3 情绪类并分级。

        从重到轻检测（优先匹配重度关键词）。
        """
        if not text:
            return None

        for level in (EmotionLevel.HEAVY, EmotionLevel.MEDIUM, EmotionLevel.LIGHT):
            keywords = _EMOTION_KEYWORDS.get(level, ())
            for keyword in keywords:
                if keyword in text:
                    return level
        return None

    def get_greeting_reply(self) -> str:
        """获取问候回复。"""
        return self._random_choice(_GREETING_TEMPLATES)

    def get_light_reply(self, text: str) -> str:
        """获取 L1 轻度情绪预设回复。"""
        best_match: tuple[int, str, tuple[str, ...]] | None = None
        for keyword, templates in _LIGHT_EMOTION_TEMPLATES.items():
            if keyword in text and (best_match is None or len(keyword) > len(best_match[0])):
                best_match = (keyword, templates)
        if best_match is not None:
            return self._random_choice(best_match[1])
        return self._random_choice(_LIGHT_DEFAULT_TEMPLATES)

    def get_medium_reply(self, text: str) -> str:
        """获取 L2 中度情绪回复（需要调用轻量 LLM）。

        此方法返回提示信息，实际 LLM 调用由 light_llm_service 处理。
        """
        return ""

    def get_heavy_safe_reply(self) -> str:
        """获取 L3 重度情绪安全兜底回复。"""
        return self._random_choice(_HEAVY_SAFE_TEMPLATES)

    def is_recall_intent(self, text: str) -> bool:
        """检测 D 类回忆意图。"""
        if not text:
            return False
        return any(p.search(text) for p in self._recall_patterns)

    def is_companion_intent(self, text: str) -> bool:
        """检测 B5/C 类陪伴/倾诉意图。"""
        if not text:
            return False
        return any(p.search(text) for p in self._companion_patterns)

    def is_long_text_vent(self, text: str, *, min_length: int = 100) -> bool:
        """检测 C 类长文本倾诉。"""
        if not text or len(text) < min_length:
            return False
        if self.is_greeting(text):
            return False
        emotion_level = self.classify_emotion(text)
        if emotion_level == EmotionLevel.HEAVY:
            return False
        return not (self.is_recall_intent(text) or self.is_companion_intent(text))

    def get_recall_guide_reply(self) -> str:
        """获取 D 类回忆引导回复。"""
        return self._random_choice((
            "你想看看之前的记录吗？点下面的入口试试~",
            "想回顾一下吗？点击「问过去的自己」入口~",
            "我可以帮你回忆之前的状态，要不要试试？",
        ))


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """编译正则表达式模式。"""
    return re.compile(pattern, re.IGNORECASE)


# ── 单例导出 ─────────────────────────────────────────────────────────────────

_quick_reply_service: QuickReplyService | None = None


def get_quick_reply_service() -> QuickReplyService:
    """获取 QuickReplyService 单例。"""
    global _quick_reply_service
    if _quick_reply_service is None:
        _quick_reply_service = QuickReplyService()
    return _quick_reply_service


__all__ = [
    "EmotionLevel",
    "QuickReplyService",
    "get_quick_reply_service",
]
