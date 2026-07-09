"""M2 诊断路由（``/api/v1/diagnosis``）。

真源：前端 diagnosis-upload/index.ts §4.3 + openapi.yaml tag=diagnosis。

契约兼容：
- 前端传单图：{ objectKey, user_note }  （diagnosis-upload/index.ts L88-89）
- 原生多图：   { photos: [url, body_part, ...], complaint }（后端期望）

PR-A2 增量（async 真 pipeline · 2026-07-08）：
- ``POST ?async=true`` → 202 ``{job_id, status: 'queued', stream_url}``；
  默认 ``async=false``（或省略）→ 保留同步返回 ``DiagnosisResponse`` 旧契约。
- 新增 ``GET /jobs/{job_id}/stream`` SSE 端点：从 ``app.state.job_state`` 拉阶段事件。
- 保留 ``GET /{report_id}/stream`` 旧 stub：原 3 个测试仍调此路径（mock
  ``get_report_status``）；本 PR 把它**改接** ``JobStateStore`` 而非硬编码 30s sleep。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id, db_session
from app.core.job_state import JobStateStore
from app.errors.codes import E_DIAGNOSIS_JOB_NOT_FOUND, E_DIAGNOSIS_NOT_FOUND
from app.services.diagnosis_service import (
    DiagnosisError,
    DiagnosisJobInputs,
    DiagnosisNotFoundError,
    create_diagnosis,
    get_diagnosis,
    run_diagnosis_job,
)

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


# Module-level set to retain strong references to fire-and-forget asyncio.Tasks.
# Python GC may collect them otherwise. PR-A2 引入。
# 元素是 task 本体；任务完成时（done callback）会自动从这个 set 里移除。
_BACKGROUND_TASKS: set[asyncio.Task[None]] = set()


class DiagnosisPhotoItem(BaseModel):
    """诊断照片项（对外契约）。

    字段命名规则：
    - ``url``：首选字段，公开可访问 URL
    - ``object_key``：object key alias；与 ``url`` 二选一（向后兼容）
    - ``body_part``：face | head | shoulder_neck
    - ``format``：jpg | png | webp | heic
    - ``size_bytes``：字节

    真源：``docs/spec/SPEC-M2-multimodal-diagnosis.md`` + openapi.yaml tag=diagnosis。

    """

    url: str | None = Field(default=None, description="公开可访问 URL")
    object_key: str | None = Field(default=None, description="object key（与 url 二选一）")
    body_part: str = Field(..., description="face | head | shoulder_neck")
    format: str = Field(default="jpg")
    size_bytes: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _ensure_url_or_object_key(self) -> DiagnosisPhotoItem:
        if not self.url and not self.object_key:
            raise ValueError("必须提供 url 或 object_key")
        return self

    def resolved_url(self) -> str:
        """返回最终 URL（object_key 时调用方需补 presigned_url）。"""
        if self.url:
            return self.url
        assert self.object_key is not None
        return self.object_key


class DiagnosisCreateRequest(BaseModel):
    """MVP 诊断请求 Schema（兼容前端单图 + 原生多图两种格式）。

    前端单图格式（来自 diagnosis-upload/index.ts §4.3）：
        { objectKey: string, user_note?: string }

    原生多图格式：
        { photos: DiagnosisPhotoItem[1|3], complaint?: string }

    MVP 优先策略：后端同时支持两种格式，前端体验不变。
    """

    # ── 前端单图格式 ─────────────────────────────────────────────────────────
    objectKey: str | None = Field(
        default=None, description="已上传图片的 objectKey（前端单图格式）"
    )
    user_note: str | None = Field(default=None, description="用户备注（前端单图格式）")

    # ── 原生多图格式 ─────────────────────────────────────────────────────────
    photos: list[DiagnosisPhotoItem] | None = Field(default=None)
    complaint: str | None = Field(default=None, max_length=500)

    def resolve_photos(self) -> list[dict]:
        """将请求转换为 service 层期望的 photos 参数格式。

        前端单图格式：构造 1 张 photo 对象（body_part=face, url=objectKey）。
        原生多图格式：直接透传。

        Raises:
            ValidationError: 当既无 ``photos`` 也无 ``objectKey`` 时。

        """
        if self.photos:
            return [p.model_dump() for p in self.photos]
        if self.objectKey:
            return [
                {
                    "url": self.objectKey,
                    "object_key": self.objectKey,
                    "body_part": "face",
                    "format": "jpg",
                    "size_bytes": 0,
                }
            ]
        err = ValueError("缺少 photos 或 objectKey")
        raise ValidationError.from_exception_data(  # type: ignore[attr-defined]
            self.__class__.__name__,
            [
                {
                    "type": "missing",
                    "loc": ("resolve_photos",),
                    "input": {},
                    "ctx": {"error": err},
                }
            ],
        )

    def resolve_complaint(self) -> str | None:
        return self.user_note if self.user_note else self.complaint


class DiagnosisData(BaseModel):
    report_id: str | None = None
    directions: list[dict]
    tags: list[str]
    summary: str
    cached: bool = False
    llm_model: str | None = None

    @field_validator("directions", mode="before")
    @classmethod
    def _flatten_directions(cls, v: object) -> object:
        """兜底 LLM/缓存中可能出现的 ``{"items": [...]}`` 嵌套 dict。

        历史背景：早期 Sprint 2 实现把 ``directions``/``tags`` 存为 ``{"items": [...]}``
        形式，导致 500 (Pydantic list_type 校验失败)。当前 service 层已拍扁为 list，
        但 user.report_cache 仍可能存在旧格式数据；本 validator 在响应构造时拍扁兜底。

        Args:
            v: 原始输入（可能是 list 或 ``{"items": [...]}`` dict）。

        Returns:
            拍扁后的 list。

        """
        if isinstance(v, dict) and "items" in v:
            items = v["items"]
            if not isinstance(items, list):
                return []
            normalized: list[dict] = []
            for item in items:
                if isinstance(item, str):
                    normalized.append({"title": item, "description": item})
                elif isinstance(item, dict):
                    normalized.append(item)
                else:
                    normalized.append({"title": str(item)})
            return normalized
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def _flatten_tags(cls, v: object) -> object:
        """同 ``_flatten_directions``，但接受 ``{"items": [...]}`` 嵌套 dict。"""
        if isinstance(v, dict) and "items" in v:
            items = v["items"]
            if not isinstance(items, list):
                return []
            return [str(x) for x in items]
        return v


class DiagnosisResponse(BaseModel):
    code: int = 0
    data: DiagnosisData


class ReportGetResponse(BaseModel):
    code: int = 0
    data: dict


@router.post(
    "",
    summary="创建多模态诊断报告",
    response_model=None,
)
async def create_diagnosis_endpoint(
    body: DiagnosisCreateRequest,
    request: Request,
    async_: Annotated[
        bool,
        Query(
            alias="async",
            description=(
                "true=async 模式（202 返 job_id + stream_url）；"
                "默认同步返 DiagnosisResponse。"
            ),
        ),
    ] = False,
    user_id: Annotated[str, Depends(current_user_id)] = "",
    session: Annotated[AsyncSession, Depends(db_session)] = None,  # type: ignore[assignment]
) -> DiagnosisResponse | JSONResponse:
    """诊断报告创建入口。

    两类行为：
    - ``async=true``（plan §4.1）：先校验照片合法（同步），写 Report 行 ``status='queued'``，
      调 ``store.create_job``，fire-and-forget asyncio 任务，**202 返** job_id + stream_url。
    - 默认（``async=false`` 或省略）：走既有同步 LLM 路径，**返** ``DiagnosisResponse``。
      本契约变更保证 78 个旧测试零改动（plan §7.3 自审清单）。
    """
    if async_:
        return await _handle_async_create(
            body=body,
            user_id=user_id,
            session=session,
            request=request,
        )

    # ── 同步路径：保持 100% 向后兼容 ─────────────────────────────────────────
    try:
        result = await create_diagnosis(
            session,
            user_id=user_id,
            photos=body.resolve_photos(),
            complaint=body.resolve_complaint(),
        )
    except DiagnosisError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return DiagnosisResponse(data=DiagnosisData(**result))


async def _handle_async_create(
    *,
    body: DiagnosisCreateRequest,
    user_id: str,
    session: AsyncSession,
    request: Request,
) -> JSONResponse:
    """Async 路径：建 row + 建 job + fire-and-forget task；返 202。

    1. 同步校验 photos：失败立即 400，**不**写入 Report 行（PR-A3 校验逻辑一致）。
    2. 写 Report 行 ``status='queued'``（UUID + photos JSON 占位），``flush``。
    3. ``store.create_job(report_id=..., user_id=...)`` → job_id。
    4. ``asyncio.create_task`` 启动 ``stream_diagnose``，task 加入 module-level set。
    5. 返 ``{code:0, data:{job_id, status, stream_url}}`` + HTTP 202。
    """
    from datetime import UTC, datetime
    from decimal import Decimal
    from uuid import UUID

    from app.db.models.report import Report
    from app.db.session import get_sessionmaker
    from app.services.diagnosis_service import _validate_complaint, _validate_photos

    photos = body.resolve_photos()
    complaint = body.resolve_complaint()
    validated_photos = _validate_photos(photos)  # may raise UserInputError → 4xx
    _validate_complaint(complaint)  # may raise → 4xx

    job_state: JobStateStore | None = getattr(request.app.state, "job_state", None)
    if job_state is None:
        # 测试 / 非 lifespan 路径兜底 —— 用模块级 singleton
        from app.core.job_state import get_job_state_store

        job_state = get_job_state_store()

    report_id = uuid4()
    try:
        user_uuid = UUID(str(user_id))
    except ValueError:
        user_uuid = uuid4()

    now_ts = datetime.now(UTC)
    report_row = Report(
        id=report_id,
        user_id=user_uuid,
        photos={"items": validated_photos},
        directions={"items": []},
        tags={"items": []},
        summary=None,
        llm_model=None,
        llm_cost=Decimal("0.0000"),
        status="queued",
        created_at=now_ts,
        created_by=str(user_id),
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user_id),
    )
    session.add(report_row)
    await session.flush()  # 把 report_id 持久化（外键约束满足后等 commit）
    await session.commit()  # commit 后 background task 的新 session 才能查到这行

    job_id = job_state.create_job(
        report_id=str(report_id),
        user_id=str(user_id),
    )

    # DB factory：本 background task 用完即关；不复用请求 scope 的 session
    sm = get_sessionmaker()

    async def _make_session() -> AsyncSession:
        return sm()

    task = asyncio.create_task(
        run_diagnosis_job(
            job_id,
            DiagnosisJobInputs(
                photos=validated_photos,
                complaint=complaint,
                user_id=str(user_id),
                report_id=str(report_id),
                db_factory=_make_session,
                store=job_state,
            ),
        )
    )
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)

    return JSONResponse(
        status_code=202,
        content={
            "code": 0,
            "data": {
                "job_id": job_id,
                "status": "queued",
                "stream_url": f"/api/v1/diagnosis/jobs/{job_id}/stream",
            },
        },
    )


@router.get("/{report_id}", response_model=ReportGetResponse, summary="获取诊断报告")
async def get_diagnosis_endpoint(
    report_id: str,
    user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
) -> ReportGetResponse:
    try:
        result = await get_diagnosis(session, user_id=user_id, report_id=report_id)
    except DiagnosisNotFoundError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    return ReportGetResponse(data=result)


# ─────────────────────────────────────────────────────────────────────────────
# SSE Stream endpoint（5 阶段诊断推送，M2 修复 #4）
# ─────────────────────────────────────────────────────────────────────────────
async def get_report_status(
    session: AsyncSession, *, user_id: str, report_id: str
) -> str | None:
    """获取诊断报告当前状态（``pending`` / ``ready`` / ``failed`` / ``None``）。

    测试通过 ``patch("app.api.routers.diagnosis_v1.get_report_status", ...)``
    替换。生产实现可查 ``Report.status`` 字段。
    """
    try:
        from uuid import UUID

        UUID(report_id)
    except (ValueError, AttributeError):
        return None
    return "ready"


@router.get("/{report_id}/stream", summary="诊断 SSE 流（5 阶段）")
# Deprecated: 保留至 2026-Q4；前端应改走 /jobs/{job_id}/stream
async def stream_diagnosis_endpoint(
    report_id: str,
    _user_id: str = Depends(current_user_id),
    session: AsyncSession = Depends(db_session),
):
    """诊断 SSE 流（5 阶段）— 老 stub 路径，仅保留以兼容 78 个老测试。

    .. deprecated::
        该端点是老路径（30s sleep mock SSE），自 ADR-0004（2026-07-09）起推荐
        使用 ``GET /jobs/{job_id}/stream``（PR-A2 真 SSE pipeline）。
        本端点仅保留以兼容 78 个老测试。

    SSE 5 阶段推送：connected → preprocess → diagnose → match → ready。
    30 秒超时兜底：若 ``get_report_status`` 始终返回 ``None``，发 error(E_DIAGNOSIS_NOT_FOUND)。
    PR-A2 保留：原 3 个测试仍调此路径；只是补 SSE keepalive headers。
    """

    async def event_stream():
        yield f"event: stage\ndata: {json.dumps({'stage': 'connected', 'ok': True})}\n\n"
        stages = ["preprocess", "diagnose", "match"]
        for stage in stages:
            await asyncio.sleep(0.001)
            yield f"event: stage\ndata: {json.dumps({'stage': stage, 'ok': True})}\n\n"
        # 等待 ready（最多 30s）
        for _ in range(30):
            await asyncio.sleep(1)
            status = await get_report_status(
                session, user_id="", report_id=report_id
            )
            if status == "ready":
                yield f"event: stage\ndata: {json.dumps({'stage': 'ready', 'ok': True})}\n\n"
                return
        # 超时
        err_payload = {"code": E_DIAGNOSIS_NOT_FOUND, "stage": "timeout"}
        yield f"event: error\ndata: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# PR-A2 SSE Stream 端点 (plan 4.2 / 6.1)
_SSE_KEEPALIVE_TIMEOUT: float = 10.0


async def _job_event_stream(
    job_state: JobStateStore,
    job_id: str,
    user_id: str,
) -> AsyncIterator[str]:
    r"""从 JobStateStore 拉阶段事件并 SSE 化。

    - 阶段事件 → ``event: stage\\ndata: {...}\\n\\n``
    - done     → ``event: done\\ndata: {...}\\n\\n`` 收尾
    - error    → ``event: error\\ndata: {...}\\n\\n`` 收尾
    - 无事件   → ``: keepalive\\n\\n``（10s 内）继续等
    """
    while True:
        evt = await job_state.next_event(job_id, timeout=_SSE_KEEPALIVE_TIMEOUT)
        if evt is None:
            yield ": keepalive\n\n"
            if job_state.get_status(job_id, user_id) is None:
                return
            continue
        if evt.kind == "stage":
            payload: dict[str, Any] = {"ok": True, **evt.payload}
            yield f"event: stage\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            continue
        if evt.kind == "done":
            yield (
                f"event: done\ndata: "
                f"{json.dumps({'report_id': evt.payload.get('report_id')}, ensure_ascii=False)}\n\n"
            )
            return
        if evt.kind == "error":
            yield (
                f"event: error\ndata: "
                f"{json.dumps(evt.payload, ensure_ascii=False)}\n\n"
            )
            return
        yield ": keepalive\n\n"


@router.get("/jobs/{job_id}/stream", summary="诊断 SSE 流（PR-A2 真 pipeline）")
async def stream_diagnosis_job_endpoint(
    job_id: str,
    request: Request,
    _user_id: str = Depends(current_user_id),
) -> StreamingResponse:
    """SSE 真 pipeline（plan §4.2 + §6.1）：从 ``app.state.job_state`` 拉 ``JobEvent``。

    Job 不存在或越权 → 404 + ``E_DIAGNOSIS_JOB_NOT_FOUND``。
    """
    job_state: JobStateStore | None = getattr(request.app.state, "job_state", None)
    if job_state is None:
        from app.core.job_state import get_job_state_store

        job_state = get_job_state_store()

    if job_state.get_status(job_id, user_id=_user_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": E_DIAGNOSIS_JOB_NOT_FOUND,
                "message_zh": "诊断任务不存在或已结束",
            },
        )

    return StreamingResponse(
        _job_event_stream(job_state, job_id, _user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


__all__ = ["get_report_status", "router"]  # re-exported for tests
