"""Unit tests for ``app.api.routers.business_v1`` CheckinCreate schema.

真源：backend/app/api/routers/business_v1.py §Schemas

覆盖：
- 前端 v2 格式：{ date, task_ids, mood_text }
- 原生后端格式：{ plan_id, day, video_id, feeling }
- 非法格式拒绝
- to_backend_format 转换
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.routers.business_v1 import CheckinCreate


class TestCheckinCreateFrontendFormat:
    """前端 v2 格式测试用例。"""

    def test_minimal_frontend_format(self) -> None:
        """前端最小格式：date + task_ids。"""
        req = CheckinCreate.model_validate({
            "date": "2026-07-07",
            "task_ids": ["task_001"],
        })
        assert req.date == "2026-07-07"
        assert req.task_ids == ["task_001"]
        assert req.mood_text is None
        assert req.plan_id is None
        assert req.day is None
        assert req.video_id is None

    def test_frontend_format_with_mood_text(self) -> None:
        """前端完整格式：date + task_ids + mood_text。"""
        req = CheckinCreate.model_validate({
            "date": "2026-07-07",
            "task_ids": ["task_001", "task_002"],
            "mood_text": "今天感觉好多了",
        })
        assert req.mood_text == "今天感觉好多了"
        assert len(req.task_ids) == 2

    def test_frontend_format_empty_task_ids(self) -> None:
        """task_ids 为空数组时应通过 schema 校验（字段存在但空）。"""
        req = CheckinCreate.model_validate({
            "date": "2026-07-07",
            "task_ids": [],
        })
        assert req.task_ids == []


class TestCheckinCreateNativeFormat:
    """原生后端格式测试用例。"""

    def test_minimal_native_format(self) -> None:
        """原生最小格式：plan_id + day + video_id。"""
        req = CheckinCreate.model_validate({
            "plan_id": "plan_001",
            "day": 1,
            "video_id": "video_001",
        })
        assert req.plan_id == "plan_001"
        assert req.day == 1
        assert req.video_id == "video_001"
        assert req.feeling is None

    def test_native_format_with_feeling(self) -> None:
        """原生完整格式含 feeling。"""
        req = CheckinCreate.model_validate({
            "plan_id": "plan_001",
            "day": 3,
            "video_id": "video_002",
            "feeling": "今天精神不错",
        })
        assert req.feeling == "今天精神不错"


class TestCheckinCreateInvalidFormat:
    """非法格式拒绝测试用例。"""

    def test_empty_body_rejected(self) -> None:
        """空 body 两种格式都不满足 → 422。"""
        with pytest.raises(ValidationError) as exc_info:
            CheckinCreate.model_validate({})
        assert "前端格式" in str(exc_info.value) or "date" in str(exc_info.value)

    def test_only_date_rejected(self) -> None:
        """仅有 date 无 task_ids → 两种格式都不满足。"""
        with pytest.raises(ValidationError):
            CheckinCreate.model_validate({"date": "2026-07-07"})

    def test_only_plan_id_rejected(self) -> None:
        """仅有 plan_id 缺少 day/video_id → 格式不完整。"""
        with pytest.raises(ValidationError):
            CheckinCreate.model_validate({"plan_id": "p_001"})

    def test_day_out_of_range_rejected(self) -> None:
        """day < 1 或 > 21 → 字段校验失败。"""
        with pytest.raises(ValidationError):
            CheckinCreate.model_validate({"plan_id": "p1", "day": 0, "video_id": "v1"})
        with pytest.raises(ValidationError):
            CheckinCreate.model_validate({"plan_id": "p1", "day": 22, "video_id": "v1"})


class TestCheckinCreateToBackendFormat:
    """to_backend_format 转换测试用例。"""

    def test_native_format_preserved(self) -> None:
        """原生格式直接透传。"""
        req = CheckinCreate.model_validate({
            "plan_id": "p_001",
            "day": 5,
            "video_id": "v_005",
            "feeling": "状态良好",
        })
        params = req.to_backend_format()
        assert params == {
            "plan_id": "p_001",
            "day": 5,
            "video_id": "v_005",
            "feeling": "状态良好",
        }

    def test_native_format_feeling_optional(self) -> None:
        """原生格式 feeling 可选。"""
        req = CheckinCreate.model_validate({
            "plan_id": "p_001",
            "day": 2,
            "video_id": "v_002",
        })
        params = req.to_backend_format()
        assert params["feeling"] is None

    def test_frontend_format_not_callable(self) -> None:
        """前端格式由 endpoint 处理，to_backend_format 抛异常。"""
        req = CheckinCreate.model_validate({
            "date": "2026-07-07",
            "task_ids": ["task_001"],
            "mood_text": "happy",
        })
        with pytest.raises(ValidationError):
            req.to_backend_format()
