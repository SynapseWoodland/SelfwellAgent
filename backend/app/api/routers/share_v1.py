"""M10 抱抱卡分享路由（``/api/v1/share``）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import current_user_id
from app.services.share_service import ShareError, generate_hug_card, get_template_meta

share_router = APIRouter(prefix="/share", tags=["share"])


class HugCardRequest(BaseModel):
    day: int
    nickname: str = "我"
    stats: dict | None = None


@share_router.post("/hug-card")
async def hug_card_endpoint(body: HugCardRequest, _user_id: str = Depends(current_user_id)) -> dict:
    try:
        return {
            "code": 0,
            "data": await generate_hug_card(
                user_id=_user_id, day=body.day, nickname=body.nickname, stats=body.stats
            ),
        }
    except ShareError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@share_router.get("/hug-card/{day}/template")
async def hug_card_template_endpoint(day: int) -> dict:
    try:
        return {"code": 0, "data": await get_template_meta(day)}
    except ShareError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


__all__ = ["HugCardRequest", "share_router"]
