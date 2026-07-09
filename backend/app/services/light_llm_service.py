"""轻量 LLM 服务：用于情绪共情 / 陪伴生成（GPT-4o-mini）。

成本控制：
- 情绪共情（B3 L2）：≤50 tokens
- 陪伴闲聊（B5/C）：≤80 tokens
- 轻量回忆摘要（D 类 P1）：≤100 tokens
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.log import logger
from app.llm import text_llm

if TYPE_CHECKING:
    pass


_EMOTION_COMPANION_PROMPT_TEMPLATE: str = """你是 Selfwell 智能管家，一个温柔、支持性的 AI 伙伴。

用户正在表达情绪，请：
1. 认真倾听，表达理解和共情
2. 不评判、不建议、不比较
3. 温柔陪伴，简洁回复
4. 不使用"但是"等转折词
5. 最多 50 个 tokens

用户输入：{user_input}

请用温柔的语气回应："""

_COMPANION_PROMPT_TEMPLATE: str = """你是 Selfwell 智能管家，用户想和你聊聊。

请：
1. 温柔、温暖地回应
2. 不评判用户的感受
3. 适当表达关心
4. 最多 80 个 tokens

用户输入：{user_input}

请回应："""

_RECALL_WITH_HISTORY_PROMPT_TEMPLATE: str = """你是 Selfwell 智能管家，用户想和你聊聊。

以下是用户之前的记录：
{history_context}

请根据这些历史记录，温柔地回应用户，并自然地引用相关内容。
1. 温柔、温暖地回应
2. 不评判用户的感受
3. 适当表达关心
4. 最多 80 个 tokens

用户输入：{user_input}

请回应："""

_C_VENT_PROMPT_TEMPLATE: str = """你是 Selfwell 智能管家，用户正在倾诉。

请：
1. 认真倾听，表达理解
2. 不评判、不建议、不比较
3. 温柔陪伴，简洁回复
4. 不使用"但是"等转折词
5. 最多 80 个 tokens

用户输入：{user_input}

请回应："""


class LightLLMService:
    """轻量 LLM 服务（用于情绪共情 / 陪伴）。

    使用 GPT-4o-mini，控制 token 数量以降低成本。
    """

    def __init__(
        self,
        *,
        emotion_max_tokens: int = 50,
        companion_max_tokens: int = 80,
        recall_max_tokens: int = 100,
        temperature: float = 0.7,
    ) -> None:
        """初始化轻量 LLM 服务。

        Args:
            emotion_max_tokens: 情绪共情回复的最大 token 数。
            companion_max_tokens: 陪伴闲聊回复的最大 token 数。
            recall_max_tokens: 回忆摘要回复的最大 token 数。
            temperature: LLM 温度参数。

        """
        self._emotion_max_tokens = emotion_max_tokens
        self._companion_max_tokens = companion_max_tokens
        self._recall_max_tokens = recall_max_tokens
        self._temperature = temperature

    def _build_messages(
        self,
        prompt_template: str,
        user_input: str,
        history_context: str | None = None,
    ) -> list[dict[str, str]]:
        """构建消息列表。

        Args:
            prompt_template: Prompt 模板字符串。
            user_input: 用户输入。
            history_context: 可选的历史上下文。

        Returns:
            消息列表。

        """
        if history_context:
            prompt = prompt_template.format(
                user_input=user_input,
                history_context=history_context,
            )
        else:
            prompt = prompt_template.format(user_input=user_input)

        return [
            {"role": "user", "content": prompt},
        ]

    def generate_emotion_response(self, text: str) -> str:
        """生成情绪共情回复（L2 中度情绪）。

        Args:
            text: 用户输入文本。

        Returns:
            LLM 生成的共情回复。

        Raises:
            Exception: LLM 调用失败时抛出异常。

        """
        from langchain_core.messages import HumanMessage

        messages = self._build_messages(
            _EMOTION_COMPANION_PROMPT_TEMPLATE,
            text,
        )
        langchain_messages = [HumanMessage(content=m["content"]) for m in messages]

        try:
            response = text_llm.invoke(langchain_messages)
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(
                "light_llm_emotion_response_generated",
                user_input_len=len(text),
                response_len=len(content),
            )
            return content.strip()
        except Exception as exc:
            logger.exception(
                "light_llm_emotion_response_failed",
                user_input_len=len(text),
                error_type=type(exc).__name__,
            )
            raise

    async def generate_emotion_response_async(self, text: str) -> str:
        """异步生成情绪共情回复（L2 中度情绪）。

        Args:
            text: 用户输入文本。

        Returns:
            LLM 生成的共情回复。

        """
        from langchain_core.messages import HumanMessage

        messages = self._build_messages(
            _EMOTION_COMPANION_PROMPT_TEMPLATE,
            text,
        )
        langchain_messages = [HumanMessage(content=m["content"]) for m in messages]

        try:
            response = await text_llm.ainvoke(langchain_messages)
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(
                "light_llm_emotion_response_async_generated",
                user_input_len=len(text),
                response_len=len(content),
            )
            return content.strip()
        except Exception as exc:
            logger.exception(
                "light_llm_emotion_response_async_failed",
                user_input_len=len(text),
                error_type=type(exc).__name__,
            )
            raise

    def generate_companion(
        self,
        text: str,
        has_history: bool = False,
        history_context: str | None = None,
    ) -> str:
        """生成陪伴回复（B5 陪伴类）。

        Args:
            text: 用户输入文本。
            has_history: 是否有历史素材。
            history_context: 可选的历史上下文字符串。

        Returns:
            LLM 生成的陪伴回复。

        """
        from langchain_core.messages import HumanMessage

        if has_history and history_context:
            messages = self._build_messages(
                _RECALL_WITH_HISTORY_PROMPT_TEMPLATE,
                text,
                history_context,
            )
        else:
            messages = self._build_messages(_COMPANION_PROMPT_TEMPLATE, text)

        langchain_messages = [HumanMessage(content=m["content"]) for m in messages]

        try:
            response = text_llm.invoke(
                langchain_messages,
                config={"max_tokens": self._companion_max_tokens},
            )
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(
                "light_llm_companion_generated",
                user_input_len=len(text),
                has_history=has_history,
                response_len=len(content),
            )
            return content.strip()
        except Exception as exc:
            logger.exception(
                "light_llm_companion_failed",
                user_input_len=len(text),
                has_history=has_history,
                error_type=type(exc).__name__,
            )
            raise

    async def generate_companion_async(
        self,
        text: str,
        has_history: bool = False,
        history_context: str | None = None,
    ) -> str:
        """异步生成陪伴回复（B5 陪伴类）。

        Args:
            text: 用户输入文本。
            has_history: 是否有历史素材。
            history_context: 可选的历史上下文字符串。

        Returns:
            LLM 生成的陪伴回复。

        """
        from langchain_core.messages import HumanMessage

        if has_history and history_context:
            messages = self._build_messages(
                _RECALL_WITH_HISTORY_PROMPT_TEMPLATE,
                text,
                history_context,
            )
        else:
            messages = self._build_messages(_COMPANION_PROMPT_TEMPLATE, text)

        langchain_messages = [HumanMessage(content=m["content"]) for m in messages]

        try:
            response = await text_llm.ainvoke(
                langchain_messages,
                config={"max_tokens": self._companion_max_tokens},
            )
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(
                "light_llm_companion_async_generated",
                user_input_len=len(text),
                has_history=has_history,
                response_len=len(content),
            )
            return content.strip()
        except Exception as exc:
            logger.exception(
                "light_llm_companion_async_failed",
                user_input_len=len(text),
                has_history=has_history,
                error_type=type(exc).__name__,
            )
            raise

    def generate_vent_response(self, text: str) -> str:
        """生成倾诉回复（C 类长文本倾诉）。

        Args:
            text: 用户输入文本。

        Returns:
            LLM 生成的倾诉回复。

        """
        from langchain_core.messages import HumanMessage

        messages = self._build_messages(_C_VENT_PROMPT_TEMPLATE, text)
        langchain_messages = [HumanMessage(content=m["content"]) for m in messages]

        try:
            response = text_llm.invoke(
                langchain_messages,
                config={"max_tokens": self._companion_max_tokens},
            )
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(
                "light_llm_vent_response_generated",
                user_input_len=len(text),
                response_len=len(content),
            )
            return content.strip()
        except Exception as exc:
            logger.exception(
                "light_llm_vent_response_failed",
                user_input_len=len(text),
                error_type=type(exc).__name__,
            )
            raise


# ── 单例导出 ─────────────────────────────────────────────────────────────────

_light_llm_service: LightLLMService | None = None


def get_light_llm_service() -> LightLLMService:
    """获取 LightLLMService 单例。"""
    global _light_llm_service
    if _light_llm_service is None:
        _light_llm_service = LightLLMService()
    return _light_llm_service


__all__ = [
    "LightLLMService",
    "get_light_llm_service",
]
