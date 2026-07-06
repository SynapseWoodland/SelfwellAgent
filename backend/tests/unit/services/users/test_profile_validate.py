"""Unit tests for ``app.services.users.profile_service.validate_profile``."""

from __future__ import annotations

import pytest

from app.core.errors import UserInputError
from app.services.users.profile_service import (
    ProfileEnumError,
    validate_profile,
)


def test_validate_profile_age_range_only() -> None:
    result = validate_profile({"age_range": "23-28"})
    assert result == {"age_range": "23-28"}


def test_validate_profile_focus_parts() -> None:
    result = validate_profile({"focus_parts": ["face", "head", "shoulder_neck"]})
    assert result["focus_parts"] == ["face", "head", "shoulder_neck"]


def test_validate_profile_focus_parts_invalid() -> None:
    with pytest.raises(ProfileEnumError):
        validate_profile({"focus_parts": ["face", "elbow"]})


def test_validate_profile_age_range_invalid() -> None:
    with pytest.raises(ProfileEnumError):
        validate_profile({"age_range": "99-100"})


def test_validate_profile_intensity_invalid() -> None:
    with pytest.raises(ProfileEnumError):
        validate_profile({"intensity": "高级"})


def test_validate_profile_preferred_time_invalid() -> None:
    with pytest.raises(ProfileEnumError):
        validate_profile({"preferred_time": "midnight"})


def test_validate_profile_sitting_hours_invalid() -> None:
    with pytest.raises(ProfileEnumError):
        validate_profile({"sitting_hours": "20h+"})


def test_validate_profile_empty() -> None:
    with pytest.raises(UserInputError):
        validate_profile({})


def test_validate_profile_full() -> None:
    result = validate_profile(
        {
            "age_range": "29-35",
            "focus_parts": ["face"],
            "intensity": "适中",
            "preferred_time": "晚",
            "sitting_hours": "4-8h",
        }
    )
    assert len(result) == 5
