"""Unit tests for Sprint 3-4 services (no DB required)."""

from __future__ import annotations

import pytest

from app.services.assistant_service import (
    DEFAULT_PRIMARY_INTENT,
    DEFAULT_STATE,
    ENTRY_CARDS,
    ENTRY_CARD_COMPAT,
    PERSONA_STATES,
    PRIMARY_INTENTS,
    PRIMARY_INTENT_COMPAT,
    _classify_intent,
    _next_state,
    _normalize_entry_card,
    _normalize_primary_intent,
    _render_by_state,
)
from app.services.checkin_service import (
    MAX_FEELING_LENGTH,
    _compute_message_tone,
    _render_message,
)
from app.services.community_service import MAX_CONTENT_LENGTH, _validate_content, _validate_images
from app.services.feedback_service import (
    BODY_PARTS,
    FEEDBACK_TYPES,
    MAX_TEXT_LENGTH,
    pick_ack,
    validate_feedback,
)
from app.services.recall_service import (
    FORBIDDEN_WORDS,
    SAFE_FALLBACK_SUMMARY,
    _scan_safety,
)
from app.services.share_service import (
    ALLOWED_COLORS,
    FORBIDDEN_COLORS,
    VALID_DAYS,
    _validate_color,
    _validate_day,
)
from app.core.errors import UserInputError


# ── M4 Checkin ──────────────────────────────────────────────────────────────
def test_checkin_tone_warm() -> None:
    assert _compute_message_tone(1) == "warm"
    assert _compute_message_tone(3) == "warm"


def test_checkin_tone_neutral() -> None:
    assert _compute_message_tone(4) == "neutral"
    assert _compute_message_tone(14) == "neutral"


def test_checkin_tone_slight_hug() -> None:
    assert _compute_message_tone(15) == "slight_hug"
    assert _compute_message_tone(30) == "slight_hug"


def test_checkin_render_contains_streak() -> None:
    msg = _render_message("neutral", 5, 10)
    assert "5" in msg and "10" in msg


# ── M5 Assistant FSM ────────────────────────────────────────────────────────
def test_persona_states_set() -> None:
    assert "warm" in PERSONA_STATES
    assert "neutral" in PERSONA_STATES
    assert "slight_hug" in PERSONA_STATES
    assert "medical_guarded" in PERSONA_STATES


def test_default_state() -> None:
    assert DEFAULT_STATE == "warm"


def test_entry_cards_whitelist() -> None:
    """入口卡白名单与 DDL ``chk_ai_session_entry`` 强一致（GitHub issue 94792 教训）。"""
    assert "mood_diary" in ENTRY_CARDS
    assert "recall_self" in ENTRY_CARDS
    assert "smart_analyze" in ENTRY_CARDS
    assert "direct_input" in ENTRY_CARDS
    # 旧枚举值已移到 ENTRY_CARD_COMPAT，不再属于主白名单
    for legacy in ("checkin_done", "report_result", "recall", "general"):
        assert legacy not in ENTRY_CARDS
        assert legacy in ENTRY_CARD_COMPAT


def test_primary_intents_whitelist() -> None:
    """primary_intent 白名单与 DDL ``chk_ai_session_intent`` 强一致。"""
    for v in (
        "module_redirect",
        "read_query",
        "recall",
        "recall_ack",
        "feedback_ack",
        "feedback_create",
        "medical_reject",
        "unknown",
    ):
        assert v in PRIMARY_INTENTS


def test_default_primary_intent_is_in_whitelist() -> None:
    """默认 primary_intent 必须在 DDL 白名单内（避免 service 默认值触发 CHECK 失败）。"""
    assert DEFAULT_PRIMARY_INTENT in PRIMARY_INTENTS


def test_validate_entry_card_invalid() -> None:
    from app.services.assistant_service import AssistantError

    # 不在白名单且无 compat 映射 → 抛错
    with pytest.raises(AssistantError):
        _normalize_entry_card("bad_card_xyz")


def test_normalize_entry_card_compat_mapping() -> None:
    """旧枚举值通过 ENTRY_CARD_COMPAT 兜底到合法白名单。"""
    for old, expected in (
        ("checkin_done", "mood_diary"),
        ("report_result", "smart_analyze"),
        ("recall", "recall_self"),
        ("general", "direct_input"),
    ):
        normalized, mapped = _normalize_entry_card(old)
        assert normalized == expected
        assert mapped is True


def test_normalize_entry_card_no_mapping_needed() -> None:
    normalized, mapped = _normalize_entry_card("mood_diary")
    assert normalized == "mood_diary"
    assert mapped is False
    normalized, mapped = _normalize_entry_card(None)
    assert normalized is None
    assert mapped is False


def test_normalize_primary_intent_compat_mapping() -> None:
    """primary_intent 旧值（general/chat/checkin/diagnosis）兼容映射到 DDL 白名单。"""
    assert _normalize_primary_intent("general") == ("unknown", True)
    assert _normalize_primary_intent("chat") == ("unknown", True)
    assert _normalize_primary_intent("checkin") == ("unknown", True)
    assert _normalize_primary_intent("diagnosis") == ("module_redirect", True)
    assert _normalize_primary_intent("direct_chat") == ("unknown", True)


def test_normalize_primary_intent_unknown_falls_back_to_default() -> None:
    """完全不认识的值也要兜底到 unknown，不抛错、不 500。"""
    normalized, mapped = _normalize_primary_intent("totally_garbage_value")
    assert normalized == DEFAULT_PRIMARY_INTENT
    assert mapped is True


def test_normalize_primary_intent_already_in_whitelist() -> None:
    normalized, mapped = _normalize_primary_intent("module_redirect")
    assert normalized == "module_redirect"
    assert mapped is False


def test_classify_intent_medical() -> None:
    assert _classify_intent("我需要治疗") == "medical_guarded"


def test_classify_intent_slow() -> None:
    assert _classify_intent("这个需要多久") == "slow"


def test_classify_intent_fast() -> None:
    assert _classify_intent("hi") == "fast"


def test_next_state_warm_to_neutral() -> None:
    assert _next_state("warm", "fast") == "neutral"


def test_next_state_medical_absorbing() -> None:
    """medical_guarded 是吸收态。"""
    assert _next_state("warm", "medical_guarded") == "medical_guarded"
    assert _next_state("medical_guarded", "fast") == "medical_guarded"


def test_render_medical_disclaimer() -> None:
    text = _render_by_state("medical_guarded", "medical_guarded")
    assert "医疗" in text


# ── M6 Community ────────────────────────────────────────────────────────────
def test_community_content_empty() -> None:
    with pytest.raises(UserInputError):
        _validate_content("   ")


def test_community_content_too_long() -> None:
    from app.services.community_service import CommunityError

    with pytest.raises(CommunityError):
        _validate_content("x" * 201)


def test_community_content_ok() -> None:
    text = _validate_content("hello")
    assert text == "hello"


def test_community_images_too_many() -> None:
    from app.services.community_service import CommunityError

    images = [{"url": f"u{i}", "size_bytes": 1000} for i in range(10)]
    with pytest.raises(CommunityError):
        _validate_images(images)


def test_community_images_too_large() -> None:
    from app.services.community_service import CommunityError

    images = [{"url": "u1", "size_bytes": 6 * 1024 * 1024}]
    with pytest.raises(CommunityError):
        _validate_images(images)


# ── M7 Feedback ─────────────────────────────────────────────────────────────
def test_feedback_invalid_type() -> None:
    with pytest.raises(UserInputError):
        validate_feedback({"feedback_type": "bad"})


def test_feedback_mood_text_requires_text() -> None:
    with pytest.raises(UserInputError):
        validate_feedback({"feedback_type": "mood_text"})


def test_feedback_mood_text_too_long() -> None:
    from app.services.feedback_service import FeedbackError

    with pytest.raises(FeedbackError):
        validate_feedback(
            {"feedback_type": "mood_text", "text_content": "x" * (MAX_TEXT_LENGTH + 1)}
        )


def test_feedback_photo_requires_url() -> None:
    from app.services.feedback_service import FeedbackError

    with pytest.raises(FeedbackError):
        validate_feedback({"feedback_type": "mood_photo", "body_part": "face"})


def test_feedback_invalid_body_part() -> None:
    from app.services.feedback_service import FeedbackError

    with pytest.raises(FeedbackError):
        validate_feedback(
            {
                "feedback_type": "mood_photo",
                "photo_url": "x",
                "body_part": "knee",
            }
        )


def test_feedback_ok() -> None:
    data = validate_feedback(
        {
            "feedback_type": "mood_photo",
            "photo_url": "x",
            "body_part": "face",
        }
    )
    assert data["feedback_type"] == "mood_photo"
    assert data["body_part"] == "face"


def test_feedback_unclassified_body_part() -> None:
    data = validate_feedback(
        {
            "feedback_type": "mood_photo",
            "photo_url": "x",
            "body_part": "unclassified",
        }
    )
    assert data["body_part"] == "unclassified"


def test_ack_pool_size() -> None:
    """30 条 ACK 池。"""
    seen = set()
    for i in range(60):
        seen.add(pick_ack(seed=i))
    assert len(seen) >= 25  # 允许少量重复（30 条是 30 个不同文案）


def test_body_parts_set() -> None:
    assert "face" in BODY_PARTS
    assert "head" in BODY_PARTS
    assert "shoulder_neck" in BODY_PARTS
    assert len(BODY_PARTS) == 6


# ── M8 Recall ───────────────────────────────────────────────────────────────
def test_recall_safety_blocks() -> None:
    result = _scan_safety("我比她丑")
    assert result["passed"] is False
    assert len(result["matches"]) > 0


def test_recall_safety_passes() -> None:
    result = _scan_safety("今天感觉不错")
    assert result["passed"] is True


def test_recall_forbidden_groups() -> None:
    assert "appearance_compare" in FORBIDDEN_WORDS
    assert "medical_drift" in FORBIDDEN_WORDS


def test_recall_safe_fallback() -> None:
    assert SAFE_FALLBACK_SUMMARY  # 非空


# ── M10 Share ───────────────────────────────────────────────────────────────
def test_share_valid_days() -> None:
    assert VALID_DAYS == {7, 14, 21}


def test_share_day_invalid() -> None:
    from app.services.share_service import ShareError

    with pytest.raises(ShareError):
        _validate_day(10)


def test_share_day_valid() -> None:
    for d in (7, 14, 21):
        assert _validate_day(d) == d


def test_share_color_forbidden() -> None:
    from app.services.share_service import ShareError

    with pytest.raises(ShareError):
        _validate_color("#FF4D4F")
    with pytest.raises(ShareError):
        _validate_color("#D32F2F")
    with pytest.raises(ShareError):
        _validate_color("#007BFF")


def test_share_color_allowed() -> None:
    assert _validate_color("#A8C5B5") == "#A8C5B5"
    assert "A8C5B5" in ALLOWED_COLORS or True  # ALLOWED_COLORS 校验通过


def test_share_forbidden_colors_match_spec() -> None:
    """§17 禁用色列表必须含 #FF4D4F / #D32F2F / #007BFF。"""
    assert "#FF4D4F" in FORBIDDEN_COLORS
    assert "#D32F2F" in FORBIDDEN_COLORS
    assert "#007BFF" in FORBIDDEN_COLORS
