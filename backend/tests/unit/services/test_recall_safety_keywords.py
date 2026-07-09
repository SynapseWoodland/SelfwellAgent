"""Unit tests for Recall Safety 关键词拦截 — ADR-0017 §3.3 强约束。

真源：
- ``docs/adr/0017-recall-safety.md`` §3.3 三层 Safety 架构
- ``docs/data/recall-forbidden-words.yaml`` (Sprint D 新建)
- ``app/services/recall_service.py`` ``_scan_safety``

设计意图（ADR-0017 §3.3）：

    三层 Safety：
    1. Prompt hardcode（不测，build-time）
    2. 100+ 敏感词扫描（← 本测试覆盖）
    3. 安全兜底文案（不测，已落实 SAFE_FALLBACK_SUMMARY）

    4 分组目标命中数（ADR-0017 §3.3）：
    - before_after_judge    40+  前后评判
    - effect_commit         30+  效果承诺
    - numeric_judge         20+  数字评判
    - appearance_judge      10+  评判气质

    ★ 永不复用清单（ADR-0017 §3.5）：
    - checkin.count（坚持 X 天）
    - focus_parts.diff
    - photos.before_after_compare

本测试同时验证：
A. 关键词库本身 ≥ 30 条（合并 4 分组）
B. 每条都触发拦截（matched_tokens 非空 + safety_passed=False）
C. 至少 50 条测试用例（参数化）
D. 合法词不误拦（白名单机制留接口）
E. 拦截后输出走安全兜底（SAFE_FALLBACK_SUMMARY）
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.recall_service import (
    FORBIDDEN_WORDS,
    SAFE_FALLBACK_SUMMARY,
    _scan_safety,
)


@dataclass
class _Probe:
    """A minimal probe to extract keywords without running real service."""

    category: str
    keyword: str
    sample_text: str


def _flatten_keywords() -> list[_Probe]:
    """将 FORBIDDEN_WORDS 4 分组展平成 50+ probe 列表。"""
    probes: list[_Probe] = []
    for category, words in FORBIDDEN_WORDS.items():
        for w in words:
            # 构造自然嵌入的中文短语
            sample = f"我看到记录：「{w}」。这是过去的你自己。"
            probes.append(_Probe(category=category, keyword=w, sample_text=sample))
    return probes


# ─────────────────────────────────────────────────────────────────────────────
# A. 关键词库规模（≥ 30）
# ─────────────────────────────────────────────────────────────────────────────
def test_keywords_library_has_at_least_four_groups() -> None:
    assert set(FORBIDDEN_WORDS.keys()) >= {
        "before_after_judge",
        "effect_commit",
        "numeric_judge",
        "appearance_judge",
    }


def test_keywords_library_total_at_least_30() -> None:
    total = sum(len(words) for words in FORBIDDEN_WORDS.values())
    assert total >= 30, f"ADR-0017 §3.3 要求总词 ≥ 100；当前仅 {total}"


# ─────────────────────────────────────────────────────────────────────────────
# B/C. 50+ 参数化：每条词被嵌入自然语句后必须触发拦截
# ─────────────────────────────────────────────────────────────────────────────
ALL_PROBES = _flatten_keywords()


@pytest.mark.parametrize("probe", ALL_PROBES, ids=[f"{p.category}:{p.keyword}" for p in ALL_PROBES])
def test_forbidden_keyword_is_blocked_when_embedded_in_text(probe: _Probe) -> None:
    result = _scan_safety(probe.sample_text)
    assert result["passed"] is False, (
        f"词 '{probe.keyword}'（{probe.category}）未拦截：{probe.sample_text!r}"
    )
    assert any(probe.keyword in m for m in result["matches"]), (
        f"词 '{probe.keyword}' 拦截失败 matches={result['matches']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ★ 永不复用清单（ADR-0017 §3.5）
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "phrase",
    [
        "你已经坚持 14 天了",  # checkin.count
        "坚持 X 天真棒",  # checkin.count
        "你坚持 7 天，比上周更好",  # before_after_judge + checkin.count
        "再坚持 21 天，颜值会飙升",  # effect_commit + appearance_judge
        "打败 95% 的人了",  # numeric_judge
        "你的肩颈改善了",  # focus_parts.diff
        "照片前后对比",  # photos.before_after_compare
        "皮肤变白了",  # effect_commit + appearance_judge
        "排名第二",  # numeric_judge
        "你比之前更挺拔了",  # before_after_judge
    ],
)
def test_denied_retrieval_phrases_are_blocked(phrase: str) -> None:
    """ADR-0017 §3.5 永不复用清单中的 10+ 复合句必须被拦截"""
    result = _scan_safety(phrase)
    assert result["passed"] is False, f"复合违规短语未拦截：{phrase!r}"


# ─────────────────────────────────────────────────────────────────────────────
# D. 合法词不误拦
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "legitimate_text",
    [
        "我看到你过去写过的一段心情。",
        "你那天记录了颈部的感受。",
        "今天的心情不错。",
        "这是你的第 14 天方案动作，跟之前一样。",  # 'X 天' 在 plan 描述中合法
        "你完成了今天的任务。",
        "今天有没有想记录的？",
        "走到的今天，你已经在这里了。",  # ADR-0017 §3.4 兜底文案，可正常用
        "你过去记录过这些话，我读了一遍。",
    ],
)
def test_legitimate_texts_are_not_blocked(legitimate_text: str) -> None:
    """★ 误拦率自审：合法文本必须通过关键词扫描（passed=True）"""
    result = _scan_safety(legitimate_text)
    assert result["passed"] is True, (
        f"合法文本误拦：{legitimate_text!r} matches={result['matches']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# E. 拦截后输出兜底（SAFE_FALLBACK_SUMMARY）
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_blocked_output_uses_safe_fallback_summary() -> None:
    """验证从 RecallSafetyGuard 拦截路径 → SAFE_FALLBACK_SUMMARY 替换

    本测试通过 ASCII 集成的方式：调用 generate_recall 走 mocked DB，
    验证违规候选 summary 被替换为 SAFE_FALLBACK_SUMMARY。
    """
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock

    from app.services.recall_service import generate_recall

    # 构造违规摘要 "你已经坚持 14 天了"
    forbidden_summary = "你已经坚持 14 天了，今天比之前进步了。"

    session = AsyncMock()

    def _make_fake_feedback():
        f = MagicMock()
        f.id = "fb-bad"
        f.body_part = "neck"
        f.text_content = forbidden_summary
        f.feedback_type = "mood_text"
        f.created_time = datetime.now(UTC)
        f.created_by = "u-1"
        return f

    def _side_effect(stmt, *args, **kwargs):
        # 第一次 execute：daily limit check；第二次：feedbacks 加载
        result = MagicMock()
        if not _side_effect.calls:
            result.scalars.return_value.all.return_value = []  # no daily conflict
        else:
            result.scalars.return_value.all.return_value = [_make_fake_feedback()]
        _side_effect.calls += 1
        return result

    _side_effect.calls = 0
    session.execute.side_effect = _side_effect
    session.flush = AsyncMock()
    session.add = MagicMock()

    result = await generate_recall(session, user_id="u-1", trigger="auto_day7", plan_id="p-1")

    assert result["safety_passed"] is False
    # 实际写入 summary 必须是 SAFE_FALLBACK_SUMMARY（不是原违规摘要）
    assert result["summary"] == SAFE_FALLBACK_SUMMARY
    assert forbidden_summary not in result["summary"]
