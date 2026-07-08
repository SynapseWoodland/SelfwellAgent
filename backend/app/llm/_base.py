"""LLM 降级链抽象基类。

两条业务链共用本文件的 retry / budget / provider_used 语义：
- ``MultimodalFallbackChain``：Doubao Seedream → Qwen VL → 规则引擎
- ``TextFallbackChain``：GLM → DeepSeek → 静态文案

注意：单个 provider 的网络、鉴权、模型返回异常只会让链路继续尝试下一个 provider，
不会阻塞诊断或聊天主流程。日预算超限仍按业务约定抛 503；月预算超限走兜底。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.core.retry import async_retry
from app.llm.budget import BudgetExceededError, MonthlyBudgetExceededError, budget_guard
from app.llm.client import LLMRequest, MultimodalRequest

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_core.language_models import BaseChatModel


@dataclass(slots=True)
class FallbackResult:
    """降级链最终结果。"""

    content: str
    provider_used: str
    attempts: int
    cost_yuan: float


class BaseFallbackChain(ABC):
    """降级链抽象基类。"""

    capability: str = ""

    def __init__(self) -> None:
        self._clients: Sequence[BaseChatModel] = self._build_clients()

    @abstractmethod
    def _build_clients(self) -> Sequence[BaseChatModel]:
        """按优先级返回 LangChain chat model 列表。"""

    @async_retry(attempts=2, min_seconds=0.2, max_seconds=1.0)
    async def _try_client(self, client: BaseChatModel, request: Any) -> Any:
        budget_guard.check()
        return await client.ainvoke(request)  # type: ignore[attr-defined]

    async def run(self, request: LLMRequest | str) -> FallbackResult:
        """串行降级调用；全部 provider 失败时返回子类兜底结果。"""
        attempts = 0
        last_error: BaseException | None = None
        for client in self._clients:
            attempts += 1
            provider = _provider_name(client)
            try:
                response = await self._try_client(client, self._coerce_payload(request))
            except MonthlyBudgetExceededError as exc:
                logger.warning(
                    "llm_chain_monthly_budget_exceeded",
                    capability=self.capability,
                    attempts=attempts,
                    provider=provider,
                )
                last_error = exc
                break
            except BudgetExceededError:
                logger.warning(
                    "llm_chain_daily_budget_exceeded",
                    capability=self.capability,
                    attempts=attempts,
                    provider=provider,
                )
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "llm_chain_attempt_failed",
                    capability=self.capability,
                    provider=provider,
                    attempts=attempts,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:200],
                )
                continue
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(
                "llm_chain_attempt_success",
                capability=self.capability,
                provider=provider,
                attempts=attempts,
            )
            return FallbackResult(
                content=content,
                provider_used=provider,
                attempts=attempts,
                cost_yuan=0.0,
            )

        logger.warning(
            "llm_chain_all_clients_failed",
            capability=self.capability,
            attempts=attempts,
            last_error_type=type(last_error).__name__ if last_error else None,
        )
        return self._fallback(request, attempts=attempts)

    @abstractmethod
    def _fallback(self, request: LLMRequest | str, *, attempts: int) -> FallbackResult:
        """全部 provider 失败后的兜底行为。"""

    @staticmethod
    def _coerce_payload(request: LLMRequest | str) -> Any:
        """把内部请求转换为 LangChain message 列表。"""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        if isinstance(request, str):
            return [HumanMessage(content=request)]
        if isinstance(request, MultimodalRequest):
            text = _join_text_messages(request)
            content: list[dict[str, Any]] = [{"type": "text", "text": text}]
            content.extend(
                {"type": "image_url", "image_url": {"url": image_url}}
                for image_url in request.images
            )
            return [HumanMessage(content=content)]

        messages: list[Any] = []
        for message in request.messages:
            if message.role == "system":
                messages.append(SystemMessage(content=message.content))
            elif message.role == "assistant":
                messages.append(AIMessage(content=message.content))
            else:
                messages.append(HumanMessage(content=message.content))
        return messages or [HumanMessage(content="请基于上下文给出回应。")]


def _join_text_messages(request: LLMRequest) -> str:
    text = "\n".join(m.content for m in request.messages if m.content).strip()
    return text or "请基于图片内容给出分析。"


def _provider_name(client: object) -> str:
    for attr in ("model_name", "model", "deployment_name"):
        value = getattr(client, attr, None)
        if isinstance(value, str) and value:
            return value
    return client.__class__.__name__


from app.core.log import logger  # noqa: E402

__all__ = ["BaseFallbackChain", "FallbackResult"]
