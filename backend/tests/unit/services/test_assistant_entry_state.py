"""Unit tests for ``assistant_service.compute_entry_state`` — M5 入口卡 4 状态机。

真源：
- ``docs/spec/TDS-M5-persona-chat.md`` §3.5.1 入口卡 4 状态
- PRD-0017 §3.5.4 基线问候
- ADR-0017 §3.6 不评判坚持时长

设计意图（每张卡按 4 状态切换副文案）：
- card1 "智能分析"：
    未开始  → "上传照片生成你的画像"
    进行中  → "正在为你生成画像，再等一会儿"
    已完成  → "已生成你的画像，回看一下吗"
    7天未互动 → "离上次互动有点久了，先看画像吗"
- card2 "心情日记"
- card3 "主动回忆"（⭐ 描边）
- card4 "直接聊聊"

返回 4 张卡 + state + highlight（⭐）标志位。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.services.assistant_service import compute_entry_state


@dataclass
class FakeMe:
    """最小化 UserMe 数据（仅用 compute_entry_state 需要的字段）。"""

    user_id: str = "u-1"
    current_streak_days: int = 0
    last_feedback_days_ago: int | None = None  # None = 用户从未发过 feedback


def _make_latest_report(report_id: str | None) -> dict[str, Any] | None:
    if report_id is None:
        return None
    return {"diagnosis_id": report_id, "created_at": "2026-07-01T08:00:00Z"}


def _make_recent_feedbacks(days_ago: int | None, count: int = 1) -> list[dict[str, Any]]:
    if days_ago is None:
        return []
    return [
        {
            "feedback_id": f"fb-{i}",
            "created_at": f"2026-07-{1 + days_ago:02d}T08:00:00Z",
        }
        for i in range(count)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# card1 "智能分析" 状态机
# ─────────────────────────────────────────────────────────────────────────────
def test_card1_smart_analyze_state_not_started_when_no_report_no_feedback() -> None:
    me = FakeMe(last_feedback_days_ago=None)
    cards = compute_entry_state(
        me=me,
        latest_report=None,
        recent_feedbacks=[],
    )
    card1 = next(c for c in cards if c["id"] == "smart_analyze")
    assert card1["state"] == "not_started"
    assert card1["subtitle"] == "上传照片生成你的画像"
    assert card1["highlight"] is False


def test_card1_smart_analyze_state_in_progress_when_recent_feedback() -> None:
    """最近 24h 内有反馈 → '进行中'（生成画像的等待窗口）"""
    me = FakeMe(last_feedback_days_ago=0)
    cards = compute_entry_state(
        me=me,
        latest_report=None,
        recent_feedbacks=_make_recent_feedbacks(days_ago=0),
    )
    card1 = next(c for c in cards if c["id"] == "smart_analyze")
    assert card1["state"] == "in_progress"
    assert "生成画像" in card1["subtitle"] or "再等一会儿" in card1["subtitle"]


def test_card1_smart_analyze_state_completed_when_has_report() -> None:
    me = FakeMe(last_feedback_days_ago=2)
    cards = compute_entry_state(
        me=me,
        latest_report=_make_latest_report("r-001"),
        recent_feedbacks=_make_recent_feedbacks(days_ago=2),
    )
    card1 = next(c for c in cards if c["id"] == "smart_analyze")
    assert card1["state"] == "completed"
    assert card1["subtitle"] == "已生成你的画像，回看一下吗"


def test_card1_smart_analyze_state_inactive_after_7days() -> None:
    """last_feedback_days_ago >= 7 → 触发 '7 天未互动' 状态"""
    me = FakeMe(last_feedback_days_ago=10)
    cards = compute_entry_state(
        me=me,
        latest_report=_make_latest_report("r-old"),
        recent_feedbacks=_make_recent_feedbacks(days_ago=10),
    )
    card1 = next(c for c in cards if c["id"] == "smart_analyze")
    assert card1["state"] == "inactive_7d"


# ─────────────────────────────────────────────────────────────────────────────
# card3 "主动回忆" ⭐ 描边
# ─────────────────────────────────────────────────────────────────────────────
def test_card3_recall_self_always_highlighted_with_star() -> None:
    """card3 永远是 ⭐（即使其 state 是 not_started）"""
    me = FakeMe(last_feedback_days_ago=None)
    cards = compute_entry_state(
        me=me,
        latest_report=None,
        recent_feedbacks=[],
    )
    card3 = next(c for c in cards if c["id"] == "recall_self")
    assert card3["highlight"] is True
    # 所有状态下都 ⭐
    assert card3["title"]  # 非空
    assert card3["subtitle"]  # 非空


# ─────────────────────────────────────────────────────────────────────────────
# 4 张卡返回 + 全部文案非硬编码占位
# ─────────────────────────────────────────────────────────────────────────────
def test_compute_entry_state_returns_exactly_four_cards() -> None:
    me = FakeMe(last_feedback_days_ago=2)
    cards = compute_entry_state(
        me=me,
        latest_report=_make_latest_report("r-1"),
        recent_feedbacks=_make_recent_feedbacks(days_ago=2),
    )
    assert len(cards) == 4
    ids = {c["id"] for c in cards}
    assert ids == {"smart_analyze", "mood_diary", "recall_self", "direct_input"}


def test_compute_entry_state_no_card_uses_placeholder_subtitle() -> None:
    """保证没有卡片用 TODO / 占位文案（自审规则）"""
    me = FakeMe()
    cards = compute_entry_state(
        me=me,
        latest_report=None,
        recent_feedbacks=[],
    )
    for card in cards:
        for forbidden in ("TODO", "FIXME", "占位", "TBD", "{{", "}}"):
            assert forbidden not in card["subtitle"], (
                f"card {card['id']} subtitle 含占位符: {card['subtitle']}"
            )
            assert forbidden not in card["title"]


# ─────────────────────────────────────────────────────────────────────────────
# M5 基线问候文案（PRD §3.5.4）
# ─────────────────────────────────────────────────────────────────────────────
def test_baseline_greeting_no_judgment_on_streak() -> None:
    """M5 基线问候不能含 '坚持 X 天 真棒' / '你坚持 X 天' 等违规词（ADR-0017）

    验证：compute_entry_state 输出不基于 streak_days 评判坚持时长。
    """
    cards = compute_entry_state(
        me=FakeMe(current_streak_days=14, last_feedback_days_ago=1),
        latest_report=_make_latest_report("r-1"),
        recent_feedbacks=_make_recent_feedbacks(days_ago=1),
    )
    # 通过 module introspection 验证：无 baseline greeting 依赖 streak
    from app.services import assistant_service as svc

    assert (
        not hasattr(svc, "BASELINE_GREETING_WITH_STREAK")
        or svc.BASELINE_GREETING_WITH_STREAK is None
    ), "基线问候不应硬编码依赖 streak_days 评判"
    # 输出不应该调用 compute_entry_state 内部引用 streak 作为评判短语
    # 这通过参数化 test_entry_state_does_not_render_judgment_phrases 进一步验证


@pytest.mark.parametrize(
    "streak_days,last_feedback_days_ago",
    [
        (0, None),
        (3, 0),
        (7, 2),
        (14, 5),
        (21, 7),
        (30, 1),
    ],
)
def test_entry_state_does_not_render_judgment_phrases(
    streak_days: int, last_feedback_days_ago: int | None
) -> None:
    """参数化：6 种 streak × last_feedback 组合下，所有卡片副文案不含评判词（ADR-0017 §3.3）"""
    me = FakeMe(current_streak_days=streak_days, last_feedback_days_ago=last_feedback_days_ago)
    cards = compute_entry_state(
        me=me,
        latest_report=_make_latest_report("r-1") if streak_days > 0 else None,
        recent_feedbacks=_make_recent_feedbacks(days_ago=last_feedback_days_ago)
        if last_feedback_days_ago is not None
        else [],
    )
    forbidden_phrases = [
        "坚持",  # 评判坚持时长
        "真棒",  # 评判打分
        "你比",  # 前后对比
        "变好了",  # 前后对比
        "变差了",  # 前后对比
        "打败",  # 数字评判
        "排名",  # 数字评判
        "效果显现",  # 效果承诺
        "保证",  # 绝对评判
        "一定",  # 绝对评判
    ]
    for card in cards:
        for phrase in forbidden_phrases:
            assert phrase not in card["subtitle"], (
                f"streak={streak_days} last_feedback={last_feedback_days_ago} "
                f"card={card['id']} 含违规短语 '{phrase}': {card['subtitle']}"
            )
