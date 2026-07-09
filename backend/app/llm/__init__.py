"""app.llm — 简化版 LLM 调用（参考 SemanticMind 架构）。

只保留：多模态（vision）+ 文本（text）两个独立实例。
无降级链、无重试、无预算守卫；异常直接抛出上层处理。
"""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import Field, BaseModel
from typing import Any, Optional, Type

from volcenginesdkarkruntime import Ark
from app.conf.app_config import app_config
from app.core.log import logger


class ArkChatModel(BaseChatModel):
    """Volcengine Ark SDK 的 LangChain 兼容封装（支持多模态调用）。

    适用于 Doubao Seed 系列模型的多模态调用。
    注意：structured output 通过 JSON 解析实现，不依赖模型的 function calling。
    """

    model: str = Field(default="doubao-seed-2.0-pro-260215")
    base_url: str = Field(default="https://ark.cn-beijing.volces.com/api/v3")
    api_key: str = Field(default="")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)

    _client: Optional[Ark] = None

    @property
    def _ark_client(self) -> Ark:
        if self._client is None:
            self._client = Ark(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        return self._client

    def _extract_text_from_response(self, response: Any) -> str:
        """从 Ark SDK Response 对象提取文本内容。

        兼容新旧 SDK 响应格式：
        - 新版(>=1.0): response.output[0].content[0].text
        - 旧版兼容: response.output_text
        """
        # 优先尝试新格式: output[].content[].text
        try:
            if hasattr(response, "output") and response.output:
                for item in response.output:
                    # 检查是否是消息类型
                    if hasattr(item, "content") and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, "text") and content_item.text:
                                return content_item.text
                    # 检查是否是文本类型
                    if hasattr(item, "text") and item.text:
                        return item.text
        except Exception:
            pass

        # 降级到旧版: output_text
        try:
            if hasattr(response, "output_text") and response.output_text:
                return response.output_text
        except Exception:
            pass

        return ""

    def _convert_messages(self, messages: list[BaseMessage]) -> list[dict[str, Any]]:
        """将 LangChain messages 转换为 Ark API 格式。"""
        ark_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                ark_messages.append({"role": "developer", "content": [{"type": "input_text", "text": msg.content}]})
            elif isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str):
                    ark_messages.append({"role": "user", "content": [{"type": "input_text", "text": content}]})
                elif isinstance(content, list):
                    ark_content = []
                    for item in content:
                        if item.get("type") == "text":
                            ark_content.append({"type": "input_text", "text": item["text"]})
                        elif item.get("type") == "image_url":
                            ark_content.append({"type": "input_image", "image_url": item["image_url"]["url"]})
                    ark_messages.append({"role": "user", "content": ark_content})
        return ark_messages

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        ark_messages = self._convert_messages(messages)

        response = self._ark_client.responses.create(
            model=self.model,
            input=ark_messages,
            temperature=self.temperature if self.temperature > 0 else 0.1,
            max_output_tokens=self.max_tokens,
        )

        text_content = self._extract_text_from_response(response)
        ai_msg = AIMessage(content=text_content)

        return ChatResult(generations=[ai_msg])

    def with_structured_output(self, schema: Type[BaseModel], **kwargs: Any) -> Runnable:
        """通过 JSON 解析实现 structured output。

        1. 生成文本响应
        2. 从文本中提取 JSON 并解析为 schema 实例
        """
        import json
        import re

        def _parse_json(text: str) -> dict:
            """从 LLM 响应中提取并解析 JSON。"""
            text = text.strip()
            # 尝试直接解析
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            # 尝试从 markdown 代码块中提取
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            # 尝试提取第一个 { 到最后一个 }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"无法从响应中解析 JSON: {text[:500]}")

        self_ref = self

        class _StructuredOutputRunnable(Runnable):
            async def ainvoke(self, input: Any, **kwargs: Any) -> BaseModel:
                # 获取消息列表
                if isinstance(input, list):
                    messages = input
                else:
                    messages = [HumanMessage(content=input)]

                # 生成响应
                ark_messages = self_ref._convert_messages(messages)
                response = self_ref._ark_client.responses.create(
                    model=self_ref.model,
                    input=ark_messages,
                    temperature=self_ref.temperature if self_ref.temperature > 0 else 0.1,
                    max_output_tokens=self_ref.max_tokens,
                )

                # 解析 JSON 并验证
                text = self_ref._extract_text_from_response(response)
                parsed = _parse_json(text)
                return schema.model_validate(parsed)

            def invoke(self, input: Any, **kwargs: Any) -> BaseModel:
                raise NotImplementedError("请使用 ainvoke() 进行异步调用")

        return _StructuredOutputRunnable()

    @property
    def _llm_type(self) -> str:
        return "ark_chat"


# ── 多模态 LLM（视觉分析：看图诊断）───────────────────────────────────────────
_multi_cfg = app_config.llm
_multimodal_llm = ArkChatModel(
    model=_multi_cfg.multi_model,
    base_url=_multi_cfg.multi_base_url or "https://ark.cn-beijing.volces.com/api/v3",
    api_key=_multi_cfg.multi_api_key,
    temperature=_multi_cfg.temperature,
    max_tokens=_multi_cfg.max_tokens,
)
logger.info(
    "llm_multimodal_initialized",
    model=_multi_cfg.multi_model,
    base_url=_multi_cfg.multi_base_url,
)

# ── 文本 LLM（智能管家聊天 / 调理常识）────────────────────────────────────────
_text_cfg = app_config.llm
_text_llm = init_chat_model(
    model=_text_cfg.model,
    model_provider="openai",
    base_url=_text_cfg.base_url,
    api_key=_text_cfg.api_key,
    temperature=_text_cfg.temperature,
    max_tokens=_text_cfg.max_tokens,
    # TBC-017 / ADR-0011 best-practice: 显式 max_retries=0 禁用 LangChain 内置
    # 重试（默认 6 次指数退避）。理由：
    # 1. 当前 LLM 调用已在外层包 `_try_client` 或业务 handler 内由调用方
    #    决定是否降级 / fallback（如降级链静态文案）；LangChain 内置 retry 会
    #    抢在外层策略前反复重试，浪费 token。
    # 2. 一旦未来恢复成完整的 for-loop fallback chain（如 TBC-018 演进路线
    #    三层可靠性栈），也必须 max_retries=0 才能让 fallback 链路生效。
    # 与 ADR-0018 (CORS) + TBC-018 §三 完整架构图的 init_chat_model 节点对齐。
    max_retries=0,
)
logger.info(
    "llm_text_initialized",
    model=_text_cfg.model,
    base_url=_text_cfg.base_url,
    max_retries=0,
)

# ── 兼容别名 ─────────────────────────────────────────────────────────────────
llm = _text_llm
multimodal_llm = _multimodal_llm
text_llm = _text_llm

__all__ = [
    "llm",
    "multimodal_llm",
    "text_llm",
]
