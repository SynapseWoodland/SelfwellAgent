"""Shared contract for ``AIMessage.context_photos`` JSONB."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContextPhotoDirection(BaseModel):
    """One smart-analysis direction stored with an AI message."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    num: int = Field(ge=1)
    title: str
    level: str
    description: str


class AIMessageContextPhotos(BaseModel):
    """Only valid shape of the ``context_photos`` JSONB payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    directions: list[ContextPhotoDirection]
    tags: list[str]
    summary: str
    injected_at: datetime


def build_ai_message_context_photos(
    *, directions: list[dict[str, Any]], tags: list[str], summary: str
) -> dict[str, Any]:
    """Normalize smart-analysis output to the locked JSONB schema."""
    normalized = [
        {
            "num": index,
            "title": str(direction.get("title", "")),
            "level": str(direction.get("level", "轻度")),
            "description": str(direction.get("description", "")),
        }
        for index, direction in enumerate(directions, start=1)
    ]
    payload = AIMessageContextPhotos(
        directions=[
            ContextPhotoDirection(**direction)  # type: ignore[arg-type]
            for direction in normalized
        ],
        tags=[str(tag) for tag in tags],
        summary=summary,
        injected_at=datetime.now(UTC),
    )
    return payload.model_dump(mode="json")


__all__ = [
    "AIMessageContextPhotos",
    "ContextPhotoDirection",
    "build_ai_message_context_photos",
]
