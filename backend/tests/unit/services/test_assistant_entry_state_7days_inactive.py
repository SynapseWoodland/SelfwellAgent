"""Unit tests for ``assistant_service.compute_entry_state`` — 7 天未互动触发。

真源：ADR-0017 §3.6 + PRD §3.5.4。

覆盖 4 张卡的 inactive_7d 状态（核心要求）：
- last_feedback_days_ago ≥ 7 → 全 4 卡进入 "inactive_7d" 状态（统一弱化文案）
- 卡片副文案不能评判 'N 天没互动' 本身（无评判原则）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.assistant_service import compute_entry_state


@dataclass
class FakeMe:
    user_id: str = "u-1"
    current_streak_days: int = 21
    last_feedback_days_ago: int | None = 0


def _feedback(days_ago: int, count: int = 1) -> list[dict[str, Any]]:
    return [
        {"feedback_id": f"fb-{i}", "created_at": f"2026-07-{(1 + days_ago):02d}T08:00:00Z"}
        for i in range(count)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# last_feedback_days_ago >= 7 → 全卡进入 inactive_7d
# ─────────────────────────────────────────────────────────────────────────────
def test_all_cards_enter_inactive_7d_when_feedback_7days_ago() -> None:
    me = FakeMe(last_feedback_days_ago=7)
    cards = compute_entry_state(
        me=me,
        latest_report={"diagnosis_id": "r-1"},
        recent_feedbacks=_feedback(days_ago=7),
    )
    states = {c["id"]: c["state"] for c in cards}
    assert all(s == "inactive_7d" for s in states.values()), states


def test_all_cards_enter_inactive_7d_when_feedback_14days_ago() -> None:
    me = FakeMe(last_feedback_days_ago=14)
    cards = compute_entry_state(
        me=me,
        latest_report={"diagnosis_id": "r-1"},
        recent_feedbacks=_feedback(days_ago=14),
    )
    states = {c["id"]: c["state"] for c in cards}
    assert all(s == "inactive_7d" for s in states.values()), states


def test_all_cards_enter_inactive_7d_when_never_recorded() -> None:
    """last_feedback_days_ago is None（用户从未发 feedback）→ 不进入 inactive_7d（应进 not_started / completed）"""
    me = FakeMe(last_feedback_days_ago=None)
    cards = compute_entry_state(
        me=me,
        latest_report=None,
        recent_feedbacks=[],
    )
    states = {c["id"]: c["state"] for c in cards}
    # 全部 = not_started 或 completed（取决于 latest_report），不应进 inactive_7d
    assert all(s != "inactive_7d" for s in states.values()), states


# ─────────────────────────────────────────────────────────────────────────────
# 6 天临界：< 7 仍正常（不是 inactive_7d）
# ─────────────────────────────────────────────────────────────────────────────
def test_all_cards_not_inactive_7d_when_feedback_6days_ago() -> None:
    me = FakeMe(last_feedback_days_ago=6)
    cards = compute_entry_state(
        me=me,
        latest_report={"diagnosis_id": "r-1"},
        recent_feedbacks=_feedback(days_ago=6),
    )
    states = {c["id"]: c["state"] for c in cards}
    # 6 天不是 7 天 → 不是 inactive_7d
    assert all(s != "inactive_7d" for s in states.values()), states


# ─────────────────────────────────────────────────────────────────────────────
# inactive_7d 文案不能评判时长（ADR-0017 §3.3）
# ─────────────────────────────────────────────────────────────────────────────
def test_inactive_7d_subtitle_no_streak_judgment() -> None:
    """inactive_7d 副文案不评判 '坚持 N 天' / '你多久没来了' 等违规短语"""
    me = FakeMe(current_streak_days=21, last_feedback_days_ago=10)
    cards = compute_entry_state(
        me=me,
        latest_report={"diagnosis_id": "r-1"},
        recent_feedbacks=_feedback(days_ago=10),
    )
    forbidden = ["坚持", "真棒", "你比", "变好", "变差", "打败", "排名", "效果"]
    for card in cards:
        for phrase in forbidden:
            assert phrase not in card["subtitle"], (
                f"inactive_7d 卡 {card['id']} 含违规短语 '{phrase}': {card['subtitle']}"
            )
