"""Schema lock for the shared ``AIMessage.context_photos`` JSONB payload."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.contracts.ai_message import (
    AIMessageContextPhotos,
    build_ai_message_context_photos,
)


@pytest.fixture
def valid_context() -> dict[str, object]:
    return {
        "directions": [
            {
                "num": 1,
                "title": "肩颈",
                "level": "轻度",
                "description": "每天做一次舒缓拉伸",
            }
        ],
        "tags": ["肩颈", "舒缓"],
        "summary": "这是那时为你整理的养护方向。",
        "injected_at": "2026-07-12T10:00:00+00:00",
    }


def test_ai_message_context_photos_requires_exact_top_level_schema(
    valid_context: dict[str, object],
) -> None:
    context = AIMessageContextPhotos.model_validate(valid_context)

    assert set(context.model_fields_set) == {
        "directions",
        "tags",
        "summary",
        "injected_at",
    }
    assert isinstance(context.injected_at, datetime)


@pytest.mark.parametrize("missing", ["directions", "tags", "summary", "injected_at"])
def test_ai_message_context_photos_rejects_missing_fields(
    valid_context: dict[str, object], missing: str
) -> None:
    invalid = {key: value for key, value in valid_context.items() if key != missing}

    with pytest.raises(ValidationError):
        AIMessageContextPhotos.model_validate(invalid)


def test_ai_message_context_photos_rejects_extra_fields(
    valid_context: dict[str, object],
) -> None:
    invalid = {**valid_context, "photos": []}

    with pytest.raises(ValidationError):
        AIMessageContextPhotos.model_validate(invalid)


def test_context_direction_requires_all_locked_fields(
    valid_context: dict[str, object],
) -> None:
    invalid = {**valid_context, "directions": [{"num": 1, "title": "肩颈"}]}

    with pytest.raises(ValidationError):
        AIMessageContextPhotos.model_validate(invalid)


def test_builder_normalizes_direction_and_emits_iso8601() -> None:
    payload = build_ai_message_context_photos(
        directions=[
            {
                "title": "肩颈",
                "level": "轻度",
                "description": "每天做一次舒缓拉伸",
                "video_id": None,
            }
        ],
        tags=["肩颈"],
        summary="温柔地回看当时的记录。",
    )

    assert payload["directions"] == [
        {
            "num": 1,
            "title": "肩颈",
            "level": "轻度",
            "description": "每天做一次舒缓拉伸",
        }
    ]
    assert isinstance(payload["injected_at"], str)
    datetime.fromisoformat(payload["injected_at"])
