"""M4 打卡路由（``/api/v1/checkins``）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.services.checkin_service import (
    CheckinError,
    create_batch_checkin,
    create_checkin,
    get_today_checkin_summary,
    list_user_checkins,
)
from app.services.plan_service import get_today_plan_tasks

checkin_router = APIRouter(prefix="/checkins", tags=["checkin"])


class CheckinCreate(BaseModel):
    """MVP 打卡请求 Schema（兼容前端 v2 + 原生后端两种格式）。

    前端 v2 传参（来自 checkin/index.ts §17.15）：
        { date: ISODate, task_ids?: string[], mood_text?: string }
        - task_ids 为空或 None = 一键打卡

    原生后端传参（兼容旧调用方）：
        { plan_id: str, day: int, video_id: str, feeling?: str }
    """

    date: str | None = Field(default=None, description="ISO 日期 YYYY-MM-DD（前端传）")
    task_ids: list[str] | None = Field(default=None, description="任务 ID 列表（前端传），空或 None = 一键打卡")
    mood_text: str | None = Field(default=None, description="心情文本（前端传）")

    plan_id: str | None = Field(default=None, description="方案 ID（原生格式）")
    day: int | None = Field(default=None, ge=1, le=21, description="第几天（原生格式）")
    video_id: str | None = Field(default=None, description="视频 ID（原生格式）")
    feeling: str | None = Field(default=None, description="心情文本（原生格式）")

    @model_validator(mode="after")
    def validate_schema(self) -> CheckinCreate:
        """必须满足两种格式之一：前端 v2 格式 OR 原生后端格式。"""
        has_v2 = self.date is not None
        has_native = (
            self.plan_id is not None
            and self.day is not None
            and self.video_id is not None
        )
        if not has_v2 and not has_native:
            raise ValueError(
                "必须提供前端格式（date）或原生格式（plan_id + day + video_id）"
            )
        return self

    @property
    def is_batch_mode(self) -> bool:
        """是否为一键打卡模式（前端 v2 格式且 task_ids 为空或 None）。"""
        return self.date is not None and (self.task_ids is None or self.task_ids == [])

    def to_backend_format(self) -> dict:
        """转换为 service 层参数（前端格式调用时抛 ValidationError）。"""
        if self.plan_id is None or self.day is None or self.video_id is None:
            err = ValueError(
                "to_backend_format 需要原生格式字段 (plan_id, day, video_id)"
            )
            payload: list[dict] = [
                {
                    "type": "missing",
                    "loc": ("to_backend_format",),
                    "input": {},
                    "ctx": {"error": err},
                }
            ]
            raise ValidationError.from_exception_data(  # type: ignore[attr-defined]
                self.__class__.__name__,
                payload,
            )
        return {
            "plan_id": self.plan_id,
            "day": self.day,
            "video_id": self.video_id,
            "feeling": self.feeling,
        }


@checkin_router.post("")
async def create_checkin_endpoint(
    body: CheckinCreate,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    try:
        if body.date is not None and body.plan_id is None:
            # 前端 v2 格式
            plan_data = await get_today_plan_tasks(
                session, user_id=user_id, day_index=body.day or 1
            )
            plan_id = plan_data.get("plan_id", "")
            if not plan_id:
                raise HTTPException(
                    400,
                    {
                        "code": "E_NO_ACTIVE_PLAN",
                        "message_zh": "请先完成诊断并获取您的21天方案",
                    },
                )

            if body.is_batch_mode:
                # 一键打卡模式
                result = await create_batch_checkin(
                    session,
                    user_id=user_id,
                    plan_id=plan_id,
                    day=body.day or 1,
                    task_ids=body.task_ids,
                    feeling=body.mood_text,
                )
                return {
                    "code": 0,
                    "data": {
                        "checkin_ids": result.get("checkin_ids", []),
                        "new_streak": result.get("new_streak", 0),
                        "ack_text": result.get("ack_text", ""),
                        "all_done_task_ids": result.get("all_done_task_ids", []),
                    },
                }
            else:
                # 单个打卡（兼容旧格式）
                task_video_map: dict[str, str] = {}
                for task in plan_data.get("tasks", []):
                    if isinstance(task, dict) and "task_id" in task and "video_id" in task:
                        task_video_map[task["task_id"]] = task["video_id"]
                first_task_id = body.task_ids[0] if body.task_ids else ""
                video_id = task_video_map.get(first_task_id, first_task_id)
                backend_params = {
                    "plan_id": plan_id,
                    "day": body.day or 1,
                    "video_id": video_id,
                    "feeling": body.mood_text,
                }
                result = await create_checkin(session, user_id=user_id, **backend_params)
                return {
                    "code": 0,
                    "data": {
                        "checkin_ids": [result.get("checkin_id")],
                        "new_streak": result.get("streak_days", 0),
                        "ack_text": result.get("message", ""),
                        "all_done_task_ids": [video_id],
                    },
                }
        else:
            # 原生后端格式
            backend_params = {
                "plan_id": body.plan_id or "",
                "day": body.day or 1,
                "video_id": body.video_id or "",
                "feeling": body.feeling,
            }
            result = await create_checkin(session, user_id=user_id, **backend_params)
            return {
                "code": 0,
                "data": {
                    "checkin_ids": [result.get("checkin_id")],
                    "new_streak": result.get("streak_days", 0),
                    "ack_text": result.get("message", ""),
                    "all_done_task_ids": [body.video_id or ""],
                },
            }
    except CheckinError as exc:
        raise HTTPException(exc.http_status, {"code": exc.code, "message_zh": exc.render_zh()})


@checkin_router.get("")
async def list_checkin_endpoint(
    plan_id: str | None = None,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    return {
        "code": 0,
        "data": await list_user_checkins(session, user_id=user_id, plan_id=plan_id),
    }


@checkin_router.get("/today", summary="今日打卡进度（home 页用）")
async def today_checkin_endpoint(
    day: int | None = Query(default=None, ge=1, le=21, description="指定第几天（默认自动计算）"),
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> dict:
    """返回 ``{date, total, done, percent, done_task_ids}``。无 plan 时全为 0。"""
    data = await get_today_checkin_summary(session, user_id=user_id, day_index=day)
    return {"code": 0, "data": data}


__all__ = ["CheckinCreate", "checkin_router"]
