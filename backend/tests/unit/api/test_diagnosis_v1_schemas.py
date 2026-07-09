"""Unit tests for ``app.api.routers.diagnosis_v1`` DiagnosisCreateRequest schema.

真源：backend/app/api/routers/diagnosis_v1.py §DiagnosisCreateRequest

覆盖：
- 前端单图格式：{ objectKey, user_note }
- 原生多图格式：{ photos: PhotoInput[3], complaint }
- resolve_photos / resolve_complaint 转换
- 非法格式拒绝
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.routers.diagnosis_v1 import DiagnosisCreateRequest, DiagnosisPhotoItem


class TestDiagnosisCreateFrontendFormat:
    """前端单图格式测试用例。"""

    def test_minimal_frontend_format(self) -> None:
        """前端最小格式：仅 objectKey。"""
        req = DiagnosisCreateRequest.model_validate({"objectKey": "uploads/test.jpg"})
        assert req.objectKey == "uploads/test.jpg"
        assert req.user_note is None
        assert req.photos is None

    def test_frontend_format_with_note(self) -> None:
        """前端完整格式：objectKey + user_note。"""
        req = DiagnosisCreateRequest.model_validate({
            "objectKey": "uploads/photo.jpg",
            "user_note": "最近总是失眠",
        })
        assert req.user_note == "最近总是失眠"

    def test_resolve_photos_frontend(self) -> None:
        """前端单图 → 构造 1 张虚假的 photo 对象。"""
        req = DiagnosisCreateRequest.model_validate({"objectKey": "test/photo.jpg"})
        photos = req.resolve_photos()
        assert len(photos) == 1
        assert photos[0]["url"] == "test/photo.jpg"
        assert photos[0]["body_part"] == "face"
        assert photos[0]["format"] == "jpg"
        assert photos[0]["size_bytes"] == 0

    def test_resolve_complaint_frontend(self) -> None:
        """前端 user_note → complaint。"""
        req = DiagnosisCreateRequest.model_validate({
            "objectKey": "test.jpg",
            "user_note": "焦虑情绪",
        })
        assert req.resolve_complaint() == "焦虑情绪"

    def test_resolve_complaint_frontend_empty(self) -> None:
        """前端无 user_note → 返回 None。"""
        req = DiagnosisCreateRequest.model_validate({"objectKey": "test.jpg"})
        assert req.resolve_complaint() is None


class TestDiagnosisCreateNativeFormat:
    """原生多图格式测试用例。"""

    def test_native_format(self) -> None:
        """原生格式：photos[3] + complaint。"""
        req = DiagnosisCreateRequest.model_validate({
            "photos": [
                {"url": "p1.jpg", "body_part": "face"},
                {"url": "p2.jpg", "body_part": "head"},
                {"url": "p3.jpg", "body_part": "shoulder_neck"},
            ],
            "complaint": "久坐肩颈不适",
        })
        assert len(req.photos) == 3
        photos = req.resolve_photos()
        assert len(photos) == 3
        assert photos[0]["url"] == "p1.jpg"

    def test_native_format_complaint(self) -> None:
        """原生 complaint 透传。"""
        req = DiagnosisCreateRequest.model_validate({
            "photos": [
                {"url": "p1.jpg", "body_part": "face"},
                {"url": "p2.jpg", "body_part": "head"},
                {"url": "p3.jpg", "body_part": "shoulder_neck"},
            ],
            "complaint": "焦虑",
        })
        assert req.resolve_complaint() == "焦虑"

    def test_native_photos_preserved(self) -> None:
        """原生 photos 原样透传。"""
        raw_photos = [
            {"url": "p1.jpg", "body_part": "face", "format": "png", "size_bytes": 1024},
            {"url": "p2.jpg", "body_part": "head"},
            {"url": "p3.jpg", "body_part": "shoulder_neck"},
        ]
        req = DiagnosisCreateRequest.model_validate({"photos": raw_photos})
        resolved = req.resolve_photos()
        assert resolved[0]["size_bytes"] == 1024
        assert resolved[0]["format"] == "png"


class TestDiagnosisCreateInvalidFormat:
    """非法格式拒绝测试用例。"""

    def test_empty_body(self) -> None:
        """空 body（无 objectKey 且无 photos）→ resolve_photos 抛异常。"""
        req = DiagnosisCreateRequest.model_validate({})
        with pytest.raises(ValidationError):
            req.resolve_photos()


class TestDiagnosisPhotoItem:
    """DiagnosisPhotoItem schema 测试用例。"""

    def test_valid_photo_input(self) -> None:
        """合法 DiagnosisPhotoItem。"""
        photo = DiagnosisPhotoItem(url="test.jpg", body_part="face")
        assert photo.url == "test.jpg"
        assert photo.body_part == "face"
        assert photo.format == "jpg"
        assert photo.size_bytes == 0

    def test_photo_input_all_fields(self) -> None:
        """DiagnosisPhotoItem 全字段。"""
        photo = DiagnosisPhotoItem(
            url="test.png",
            body_part="head",
            format="png",
            size_bytes=2048,
        )
        assert photo.size_bytes == 2048
        assert photo.format == "png"

    def test_photo_input_empty_url_rejected(self) -> None:
        """Url 为空 → 校验失败。"""
        with pytest.raises(ValidationError):
            DiagnosisPhotoItem(url="", body_part="face")
