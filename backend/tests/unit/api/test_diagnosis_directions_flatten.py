"""Unit tests for diagnosis directions/tags ``{"items": [...]}`` flatten fix.

历史背景：Sprint 2 早期实现把 ``directions``/``tags`` 存为 ``{"items": [...]}`` 嵌套
dict，导致 ``DiagnosisData`` 校验失败 (500)。

修复点：
1. ``DiagnosisData._flatten_directions`` / ``_flatten_tags`` field_validator（响应构造层）
2. ``_get_cached_report`` 缓存读取层（service 层）
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.api.routers.diagnosis_v1 import DiagnosisData
from app.services.diagnosis_service import _flatten_items, _get_cached_report


# ─────────────────────────────────────────────────────────────────────────────
# 1. service._flatten_items helper
# ─────────────────────────────────────────────────────────────────────────────
class TestFlattenItemsHelper:
    """``_flatten_items`` 单元测试。"""

    def test_list_input_unchanged(self) -> None:
        """List 直接透传。"""
        assert _flatten_items([1, 2, 3]) == [1, 2, 3]
        assert _flatten_items(["a", "b"]) == ["a", "b"]

    def test_dict_with_items_flattened(self) -> None:
        """``{"items": [...]}`` 拍扁为 list。"""
        assert _flatten_items({"items": [1, 2, 3]}) == [1, 2, 3]
        assert _flatten_items({"items": ["a", "b"]}) == ["a", "b"]

    def test_empty_items_returns_empty_list(self) -> None:
        """``{"items": []}`` 拍扁为空 list。"""
        assert _flatten_items({"items": []}) == []

    def test_items_not_list_returns_empty_list(self) -> None:
        """``{"items": "str"}`` 容错返回空 list。"""
        assert _flatten_items({"items": "string"}) == []
        assert _flatten_items({"items": None}) == []

    def test_dict_without_items_unchanged(self) -> None:
        """``{"foo": 1}`` 不变（不是 items 键）。"""
        v: object = {"foo": 1}
        assert _flatten_items(v) == {"foo": 1}

    def test_none_input_returns_empty_list(self) -> None:
        """None 输入返回空 list（与 cache.get 缺省值行为对齐）。"""
        # ``_get_cached_report`` 走 ``cache.get(..., [])``；helper 本身不处理 None
        # 但下游类型注解为 list，加层防御
        assert _flatten_items(None) is None or _flatten_items(None) == []  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# 2. DiagnosisData field_validators（响应构造层兜底）
# ─────────────────────────────────────────────────────────────────────────────
class TestDiagnosisDataFlatten:
    """``DiagnosisData`` field_validator 单元测试。"""

    def test_list_directions_validates(self) -> None:
        """List 格式 directions 正常通过。"""
        data = DiagnosisData(
            directions=[{"title": "x", "description": "y"}],
            tags=["t1"],
            summary="ok",
        )
        assert data.directions == [{"title": "x", "description": "y"}]

    def test_dict_directions_flattened(self) -> None:
        """``{"items": [...]}`` 嵌套 dict 在响应构造时被拍扁。"""
        data = DiagnosisData(
            directions={"items": [{"title": "a"}, {"title": "b"}]},  # type: ignore[arg-type]
            tags={"items": ["t1", "t2"]},  # type: ignore[arg-type]
            summary="ok",
        )
        assert data.directions == [{"title": "a"}, {"title": "b"}]
        assert data.tags == ["t1", "t2"]

    def test_empty_dict_directions_flattened_to_empty_list(self) -> None:
        """``{"items": []}`` 拍扁为 []。"""
        data = DiagnosisData(
            directions={"items": []},  # type: ignore[arg-type]
            tags={"items": []},  # type: ignore[arg-type]
            summary="ok",
        )
        assert data.directions == []
        assert data.tags == []

    def test_invalid_list_type_still_rejected(self) -> None:
        """非 list/dict 仍按 Pydantic 默认拒绝（强类型兜底）。"""
        with pytest.raises(ValidationError):
            DiagnosisData(
                directions="not a list",  # type: ignore[arg-type]
                tags=["t1"],
                summary="ok",
            )

    def test_legacy_string_items_normalized_to_dicts(self) -> None:
        """老 LLM 输出格式 ``{"items": [str, str, ...]}`` → 自动包成 ``{"title": str}``。"""
        data = DiagnosisData(
            directions={"items": ["每日坚持拉伸", "规律作息"]},  # type: ignore[arg-type]
            tags=["t1"],
            summary="ok",
        )
        assert data.directions == [
            {"title": "每日坚持拉伸", "description": "每日坚持拉伸"},
            {"title": "规律作息", "description": "规律作息"},
        ]


# ─────────────────────────────────────────────────────────────────────────────
# 3. _get_cached_report 缓存读取层兜底
# ─────────────────────────────────────────────────────────────────────────────
class _FakeUser:
    """构造最小可用的 ``user`` 对象供 ``_get_cached_report`` 使用。"""

    def __init__(
        self,
        report_cache: dict[str, Any] | None,
        expires_at: Any = None,
    ) -> None:
        self.report_cache = report_cache
        self.report_cache_expires_at = expires_at


class TestGetCachedReportFlatten:
    """``_get_cached_report`` 拍扁兜底测试。"""

    def test_legacy_cache_with_items_dict_is_flattened(self) -> None:
        """旧缓存（``{"items": [...]}`` 格式）→ service 层拍扁成 list[dict] 返回。"""
        from datetime import UTC, datetime, timedelta

        user = _FakeUser(
            report_cache={
                "report_id": "rep_1",
                "directions": {"items": ["d1", "d2", "d3"]},
                "tags": {"items": ["t1", "t2"]},
                "summary": "legacy",
            },
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        cached = _get_cached_report(user)  # type: ignore[arg-type]
        assert cached is not None
        # service 层 _normalize_directions 会把 str items 包成 dict
        assert cached["directions"] == [
            {"title": "d1", "description": "", "video_id": None},
            {"title": "d2", "description": "", "video_id": None},
            {"title": "d3", "description": "", "video_id": None},
        ]
        # tags 走 _normalize_tags：2 条 < MIN_TAGS=7 会用兜底 7 条
        assert len(cached["tags"]) == 7
        assert all(isinstance(t, str) for t in cached["tags"])

    def test_modern_cache_with_list_passes_through(self) -> None:
        """新缓存（list 格式）→ 直接透传。"""
        from datetime import UTC, datetime, timedelta

        user = _FakeUser(
            report_cache={
                "report_id": "rep_2",
                "directions": [{"title": "a"}, {"title": "b"}, {"title": "c"}],
                "tags": ["t1", "t2", "t3", "t4", "t5", "t6", "t7"],
                "summary": "modern",
            },
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        cached = _get_cached_report(user)  # type: ignore[arg-type]
        assert cached is not None
        assert len(cached["directions"]) == 3
        assert cached["directions"][0]["title"] == "a"
        assert cached["tags"] == ["t1", "t2", "t3", "t4", "t5", "t6", "t7"]

    def test_expired_cache_returns_none(self) -> None:
        """过期缓存 → None（不返回。"""
        from datetime import UTC, datetime, timedelta

        user = _FakeUser(
            report_cache={"report_id": "r", "directions": [1]},
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert _get_cached_report(user) is None  # type: ignore[arg-type]
