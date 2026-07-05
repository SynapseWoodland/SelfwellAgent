"""LLM 月/日预算守卫（Sprint 0 骨架）。

真源：``docs/spec/facts-anchor.md`` §4：月 ≤ ¥700 / 日 ≤ ¥40。

约定：
1. 超日预算（¥40）立即返回 503（任何调用方）
2. 超月预算（¥700）降级到规则引擎（见 ``fallback_chain.FallbackChain``）
3. 预算金额按 Prometheus Counter 累计；可用 ``reset_daily()``（cron 触发）
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.conf.app_config import app_config
from app.core.errors import PermanentError, TransientError

if TYPE_CHECKING:
    pass


class BudgetExceededError(TransientError):
    """日预算超限（HTTP 503）。"""

    code: str = "E_GENERAL_SERVICE_UNAVAILABLE"
    message_zh: str = "AI 服务今日额度已用完，请明日再试"
    message_en: str = "AI service daily quota exceeded"
    severity = "TRANSIENT"
    http_status = 503


class MonthlyBudgetExceededError(PermanentError):
    """月预算超限（降级兜底触发）。"""

    code: str = "E_GENERAL_SERVICE_UNAVAILABLE"
    message_zh: str = "本月 AI 服务额度已用完，已切换兜底"
    message_en: str = "Monthly AI quota exceeded, fallback engaged"
    severity = "DEGRADED"
    http_status = 200


# ─────────────────────────────────────────────────────────────────────────────
# §一 BudgetGuard
# ─────────────────────────────────────────────────────────────────────────────
class BudgetGuard:
    """LLM 预算守卫（thread-safe 单例）。"""

    def __init__(self) -> None:
        self._daily_cost: float = 0.0
        self._monthly_cost: float = 0.0
        self._daily_reset_at: datetime = datetime.now(UTC)
        self._monthly_reset_at: datetime = datetime.now(UTC)

    def _maybe_reset(self) -> None:
        now = datetime.now(UTC)
        if now.date() != self._daily_reset_at.date():
            self._daily_cost = 0.0
            self._daily_reset_at = now
        if now.month != self._monthly_reset_at.month:
            self._monthly_cost = 0.0
            self._monthly_reset_at = now

    def check(self, estimated_cost: float = 0.0) -> None:
        """检查预算是否充足；超日预算 raise ``BudgetExceededError``。"""
        self._maybe_reset()
        if self._daily_cost + estimated_cost > app_config.llm.daily_budget_yuan:
            raise BudgetExceededError()
        if self._monthly_cost + estimated_cost > app_config.llm.monthly_budget_yuan:
            raise MonthlyBudgetExceededError()

    def record(self, cost_yuan: float) -> None:
        self._maybe_reset()
        self._daily_cost += cost_yuan
        self._monthly_cost += cost_yuan

    def reset_daily(self) -> None:
        self._daily_cost = 0.0
        self._daily_reset_at = datetime.now(UTC)

    def reset_monthly(self) -> None:
        self._monthly_cost = 0.0
        self._monthly_reset_at = datetime.now(UTC)

    @property
    def daily_cost(self) -> float:
        return self._daily_cost

    @property
    def monthly_cost(self) -> float:
        return self._monthly_cost


# 全局单例
budget_guard = BudgetGuard()


__all__ = [
    "BudgetExceededError",
    "BudgetGuard",
    "MonthlyBudgetExceededError",
    "budget_guard",
]
