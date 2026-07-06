"""Unit tests for diagnosis_service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.diagnosis_service import (
    ALLOWED_IMAGE_FORMATS,
    DiagnosisNotFoundError,
    _validate_complaint,
    _validate_photos,
)


def test_validate_photos_ok() -> None:
    photos = [
        {"url": "https://x/f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 1000},
        {"url": "https://x/h.jpg", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {
            "url": "https://x/s.jpg",
            "body_part": "shoulder_neck",
            "format": "jpg",
            "size_bytes": 3000,
        },
    ]
    result = _validate_photos(photos)
    assert len(result) == 3
    assert result[0]["body_part"] == "face"


def test_validate_photos_wrong_count() -> None:
    from app.core.errors import UserInputError

    with pytest.raises(UserInputError):
        _validate_photos([{"url": "x", "body_part": "face"}])


def test_validate_photos_bad_format() -> None:
    from app.services.diagnosis_service import DiagnosisError

    photos = [
        {"url": "https://x/f.gif", "body_part": "face", "format": "gif", "size_bytes": 1000},
        {"url": "https://x/h.jpg", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {
            "url": "https://x/s.jpg",
            "body_part": "shoulder_neck",
            "format": "jpg",
            "size_bytes": 3000,
        },
    ]
    with pytest.raises(DiagnosisError) as exc_info:
        _validate_photos(photos)
    assert "format" in exc_info.value.code.lower()


def test_validate_photos_too_large() -> None:
    from app.services.diagnosis_service import DiagnosisError

    photos = [
        {"url": "x", "body_part": "face", "format": "jpg", "size_bytes": 20 * 1024 * 1024},
        {"url": "x", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {"url": "x", "body_part": "shoulder_neck", "format": "jpg", "size_bytes": 3000},
    ]
    with pytest.raises(DiagnosisError) as exc_info:
        _validate_photos(photos)
    assert exc_info.value.code == "E_DIAGNOSIS_IMAGE_TOO_LARGE"


def test_validate_complaint_none() -> None:
    assert _validate_complaint(None) is None


def test_validate_complaint_too_long() -> None:
    from app.services.diagnosis_service import DiagnosisError

    with pytest.raises(DiagnosisError) as exc_info:
        _validate_complaint("x" * 600)
    assert "TOO_LONG" in exc_info.value.code


def test_validate_photos_wrong_body_part() -> None:
    from app.core.errors import UserInputError

    photos = [
        {"url": "x", "body_part": "leg", "format": "jpg", "size_bytes": 1000},
        {"url": "x", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {"url": "x", "body_part": "shoulder_neck", "format": "jpg", "size_bytes": 3000},
    ]
    with pytest.raises(UserInputError):
        _validate_photos(photos)


def test_allowed_image_formats_contains_jpg_png() -> None:
    assert "jpg" in ALLOWED_IMAGE_FORMATS
    assert "png" in ALLOWED_IMAGE_FORMATS
