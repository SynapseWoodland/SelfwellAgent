"""Unit tests for diagnosis directions/tags normalization (Hotfix-2).

历史背景（2026-07-07）：
- 旧 Sprint 2 实现把 ``user.report_cache.directions`` 存为 ``{"items": [...]}`` 嵌套 dict
- Mock LLM/真实 LLM 可能返回 ``directions`` 为 str list（``["方向 1", ...]``）
  或 dict list（``[{"title", "description", ...}]``）
- 上层 ``DiagnosisData`` (Pydantic) 期望 ``directions: list[dict]``，导致 500

修复（service 层 ``_normalize_directions`` / ``_normalize_tags`` / ``_flatten_items``）：
- ``{"items": [...]}`` → ``[...]`` (拍扁)
- str list → dict list（每个 str 包装成 ``{"title": str, "description": "", "video_id": None}``）
- dict list → dict list（normalize fields）
- 不够条数 → 用兜底 dict 补齐到 ``MIN_DIRECTIONS``
"""

from __future__ import annotations

from app.services.diagnosis_service import (
    MAX_DIRECTIONS,
    MIN_DIRECTIONS,
    _flatten_items,
    _normalize_directions,
    _normalize_tags,
)


def test_flatten_items_with_items_key() -> None:
    """``{"items": [...]}`` 应被拍扁为 ``[...]``。"""
    assert _flatten_items({"items": ["a", "b", "c"]}) == ["a", "b", "c"]


def test_flatten_items_passthrough_list() -> None:
    """已经是 list 的输入应该原样返回。"""
    assert _flatten_items(["a", "b"]) == ["a", "b"]


def test_flatten_items_empty_dict_returns_empty_list() -> None:
    """``{"items": <非 list>}`` 应回退为 ``[]``。"""
    assert _flatten_items({"items": "not a list"}) == []


def test_normalize_directions_from_str_list() -> None:
    """LLM 返回 ``list[str]`` 时，每个 str 应包装成 ``{title, description, video_id}``。"""
    raw = ["肩颈拉伸", "规律作息", "放松神经", "加强锻炼"]
    result = _normalize_directions(raw)
    assert len(result) == 4
    assert all(isinstance(d, dict) for d in result)
    assert result[0]["title"] == "肩颈拉伸"
    assert result[0]["description"] == ""
    assert result[0]["video_id"] is None


def test_normalize_directions_from_dict_list() -> None:
    """LLM 返回 ``list[dict]`` 时，应保留 title/description/video_id。"""
    raw = [
        {"title": "T1", "description": "D1", "video_id": "v1"},
        {"title": "T2", "description": "D2", "video_id": None},
        {"title": "T3", "description": "D3", "video_id": None},
    ]
    result = _normalize_directions(raw)
    assert len(result) == 3
    assert result[0] == {"title": "T1", "description": "D1", "video_id": "v1"}
    assert result[1]["video_id"] is None


def test_normalize_directions_empty_list_uses_fallback() -> None:
    """输入空 list 或 None 时，应用兜底填充到 ``MIN_DIRECTIONS``。"""
    result = _normalize_directions([])
    assert len(result) == MIN_DIRECTIONS
    assert all(isinstance(d, dict) and d.get("title") for d in result)


def test_normalize_directions_none_uses_fallback() -> None:
    """None 输入也应使用兜底。"""
    result = _normalize_directions(None)  # type: ignore[arg-type]
    assert len(result) == MIN_DIRECTIONS


def test_normalize_directions_too_few_is_padded() -> None:
    """少于 ``MIN_DIRECTIONS`` 条时，应用兜底补齐。"""
    raw = ["仅一条"]
    result = _normalize_directions(raw)
    assert len(result) == MIN_DIRECTIONS


def test_normalize_directions_capped_at_max() -> None:
    """多于 ``MAX_DIRECTIONS`` 条时，应被截断。"""
    raw = [f"方向{i}" for i in range(20)]
    result = _normalize_directions(raw)
    assert len(result) == MAX_DIRECTIONS


def test_normalize_directions_mixed_types() -> None:
    """混合输入（dict + str）应统一处理。"""
    raw = [
        {"title": "T1", "description": "D1", "video_id": None},
        "S2",
        {"title": "T3", "description": "D3", "video_id": "v3"},
        "S4",
    ]
    result = _normalize_directions(raw)
    assert len(result) == 4
    assert result[0]["title"] == "T1"
    assert result[1]["title"] == "S2"
    assert result[1]["description"] == ""
    assert result[2]["title"] == "T3"
    assert result[3]["title"] == "S4"


def test_normalize_tags_passthrough() -> None:
    """Tags 已经是 ``list[str]``（>= MIN_TAGS 条）时应原样返回。"""
    raw = ["肩颈", "气色", "睡眠", "情绪", "压力", "活力", "气质", "免疫"]
    result = _normalize_tags(raw)
    assert result == ["肩颈", "气色", "睡眠", "情绪", "压力", "活力", "气质", "免疫"]


def test_normalize_tags_from_items_dict() -> None:
    """``{"items": [...]}`` 嵌套形态应被拍扁。"""
    nested = {"items": ["肩颈不适", "情绪调节", "气色改善", "活力提升", "免疫增强", "压力释放", "气质提升", "睡眠改善"]}
    flat = _flatten_items(nested)
    result = _normalize_tags(flat)  # type: ignore[arg-type]
    assert result == ["肩颈不适", "情绪调节", "气色改善", "活力提升", "免疫增强", "压力释放", "气质提升", "睡眠改善"]


def test_normalize_tags_too_few_uses_fallback() -> None:
    """少于 ``MIN_TAGS`` 条时应用兜底。"""
    result = _normalize_tags(["only"])
    assert len(result) >= 7  # MIN_TAGS
