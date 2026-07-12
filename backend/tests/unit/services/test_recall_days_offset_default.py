"""Contract tests for recall ``days_offset`` defaults and forwarding."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.routers.butler_v1 import RecallGenerateRequest, generate_recall_endpoint
from app.services.recall_service import generate_recall


def _scalars_result(values: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


async def _generate(days_offset: int | None = None) -> dict[str, object]:
    session = AsyncMock()
    session.execute.side_effect = [_scalars_result([]), _scalars_result([])]
    session.add = MagicMock()
    session.flush = AsyncMock()
    kwargs: dict[str, object] = {
        "session": session,
        "user_id": "user-recall-days",
        "trigger": "auto_day7",
    }
    if days_offset is not None:
        kwargs["days_offset"] = days_offset
    return await generate_recall(**kwargs)


@pytest.mark.asyncio
async def test_recall_days_offset_defaults_to_seven() -> None:
    result = await _generate()

    assert result["days_offset"] == 7


@pytest.mark.asyncio
@pytest.mark.parametrize("days_offset", [3, 7, 14])
async def test_recall_days_offset_value_is_applied(days_offset: int) -> None:
    result = await _generate(days_offset)

    assert result["days_offset"] == days_offset


@pytest.mark.asyncio
async def test_recall_router_forwards_default_seven(monkeypatch: pytest.MonkeyPatch) -> None:
    generate_mock = AsyncMock(return_value={"days_offset": 7})
    monkeypatch.setattr("app.api.routers.butler_v1.generate_recall", generate_mock)

    response = await generate_recall_endpoint(
        body=RecallGenerateRequest(),
        user_id="user-router-default",
        session=AsyncMock(),
    )

    assert response["data"]["days_offset"] == 7
    assert generate_mock.await_args.kwargs["days_offset"] == 7
