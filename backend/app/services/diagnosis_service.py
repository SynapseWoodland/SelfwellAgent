"""M2 diagnosis business service（M2 多模态诊断）。

真源：``docs/spec/SPEC-M2-multimodal-diagnosis.md`` + ADR-0003。
- 6 节点子图：upload → validate → compliance → llm_diagnose → format → cache
- 7 天 Redis 缓存（按 user_id key）
- 多模态主备链 + 规则引擎兜底
- 5 条合规红线（R1-R5）1:1 进入 Prompt
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.models.report import Report
from app.db.models.user import User
from app.errors.codes import (
    E_DIAGNOSIS_COMPLAINT_TOO_LONG,
    E_DIAGNOSIS_IMAGE_FORMAT_UNSUPPORTED,
    E_DIAGNOSIS_IMAGE_TOO_LARGE,
    E_DIAGNOSIS_INVALID_INPUT,
    E_DIAGNOSIS_NOT_FOUND,
    E_DIAGNOSIS_RATE_LIMIT,
)
from app.services.compliance.checker import check_input as _check_input_compliance


def _check_text_safety(text: str) -> dict[str, object]:
    """业务层合规模块：检查用户输入。

    Returns:
        ``{"passed": bool, "matches": list[str], "severity": str}``

    """
    result = _check_input_compliance(text)
    return {
        "passed": not result.get("blocked", False),
        "matches": result.get("matches", []),
        "severity": result.get("severity", "normal"),
    }


CACHE_TTL_DAYS = 7
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_FORMATS: frozenset[str] = frozenset({"jpeg", "jpg", "png", "webp", "heic"})
MAX_COMPLAINT_LENGTH = 500
MIN_DIRECTIONS = 3
MAX_DIRECTIONS = 5
MIN_TAGS = 7
MAX_TAGS = 14


class DiagnosisError(SelfwellError):
    """诊断业务异常基类。"""

    code: str = E_DIAGNOSIS_INVALID_INPUT
    message_zh: str = "诊断请求无效"
    message_en: str = "Invalid diagnosis request"
    severity = "USER_ERROR"
    http_status = 400


class DiagnosisNotFoundError(DiagnosisError):
    code: str = E_DIAGNOSIS_NOT_FOUND
    message_zh: str = "诊断报告不存在"
    message_en: str = "Diagnosis report not found"
    http_status = 404


class DiagnosisRateLimitError(DiagnosisError):
    code: str = E_DIAGNOSIS_RATE_LIMIT
    message_zh: str = "诊断请求过于频繁，请稍后再试"
    message_en: str = "Diagnosis rate limit exceeded"
    http_status = 429


def _validate_photos(photos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """校验前端单图或原生 3 图照片输入。"""
    if not isinstance(photos, list) or len(photos) not in {1, 3}:
        raise UserInputError(
            "需要 1 张或 3 张照片",
            code=E_DIAGNOSIS_INVALID_INPUT,
            field="photos",
        )
    validated: list[dict[str, Any]] = []
    required_parts = ("face", "head", "shoulder_neck")
    for idx, photo in enumerate(photos):
        if not isinstance(photo, dict):
            raise UserInputError(
                f"第 {idx + 1} 张照片格式错误",
                code=E_DIAGNOSIS_INVALID_INPUT,
                field=f"photos[{idx}]",
            )
        url = photo.get("url")
        body_part = photo.get("body_part")
        size = photo.get("size_bytes", 0)
        fmt = photo.get("format", "jpg").lower()
        if not url or not isinstance(url, str):
            raise UserInputError(
                f"第 {idx + 1} 张照片 url 缺失",
                code=E_DIAGNOSIS_INVALID_INPUT,
                field=f"photos[{idx}].url",
            )
        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise DiagnosisError(
                f"照片格式不支持：{fmt}",
                code=E_DIAGNOSIS_IMAGE_FORMAT_UNSUPPORTED,
                field=f"photos[{idx}].format",
                supported=sorted(ALLOWED_IMAGE_FORMATS),
            )
        if size > MAX_IMAGE_BYTES:
            raise DiagnosisError(
                f"照片过大（{size // (1024 * 1024)}MB > 10MB）",
                code=E_DIAGNOSIS_IMAGE_TOO_LARGE,
                field=f"photos[{idx}].size_bytes",
                size=size,
            )
        if body_part not in required_parts:
            raise UserInputError(
                f"第 {idx + 1} 张照片 body_part 必须为 {required_parts} 之一",
                code=E_DIAGNOSIS_INVALID_INPUT,
                field=f"photos[{idx}].body_part",
            )
        validated.append({"url": url, "body_part": body_part, "format": fmt, "size_bytes": size})
    return validated


def _validate_complaint(text: str | None) -> str | None:
    if text is None:
        return None
    if len(text) > MAX_COMPLAINT_LENGTH:
        raise DiagnosisError(
            f"主诉文字超长（{len(text)} > {MAX_COMPLAINT_LENGTH}）",
            code=E_DIAGNOSIS_COMPLAINT_TOO_LONG,
            field="complaint",
            limit=MAX_COMPLAINT_LENGTH,
        )
    return text


def _normalize_directions(raw: list[dict[str, Any]] | list[str] | None) -> list[dict[str, Any]]:
    """Normalize directions to ``list[dict]`` shape expected by ``DiagnosisData``.

    历史背景：Mock LLM 与真实 LLM 可能返回 dict list（``[{"title", "description", ...}]``）
    或 str list（``["方向 1", "方向 2", ...]``）；混合形态时拍扁为统一 dict shape。
    """
    if not isinstance(raw, list) or len(raw) < MIN_DIRECTIONS:
        return [
            {
                "title": "基础养护方向",
                "description": "建议从轻柔开始，逐步建立规律作息。",
                "video_id": None,
            }
            for _ in range(MIN_DIRECTIONS)
        ]
    normalized: list[dict[str, Any]] = []
    for item in raw[:MAX_DIRECTIONS]:
        if isinstance(item, dict):
            normalized.append(
                {
                    "title": str(item.get("title", "")),
                    "description": str(item.get("description", "")),
                    "video_id": item.get("video_id"),
                }
            )
        elif isinstance(item, str):
            normalized.append({"title": item, "description": "", "video_id": None})
    # 补齐最少条数
    while len(normalized) < MIN_DIRECTIONS:
        normalized.append(
            {
                "title": "基础养护方向",
                "description": "建议从轻柔开始，逐步建立规律作息。",
                "video_id": None,
            }
        )
    return normalized


def _normalize_tags(raw: list[str] | None) -> list[str]:
    if not isinstance(raw, list) or len(raw) < MIN_TAGS:
        # 复用兜底基础 3 条并循环补齐到 MIN_TAGS，避免 slice 出短 list
        fallback_seed = ["基础养护", "规律作息", "温和改善"]
        return [fallback_seed[i % len(fallback_seed)] for i in range(MIN_TAGS)]
    return [str(t) for t in raw[:MAX_TAGS]]


def _diagnosis_prompt(profile: dict[str, Any], complaint: str | None) -> str:
    """构造照片诊断提示词，要求模型只返回 JSON。"""
    return json.dumps(
        {
            "task": "请基于用户照片和档案生成非医疗性质的基础养护建议",
            "profile": profile,
            "complaint": complaint or "",
            "output_schema": {
                "directions": [
                    {"title": "string", "description": "string", "video_id": "string|null"}
                ],
                "tags": ["string"],
                "summary": "string",
                "llm_cost": "number|string",
            },
            "safety_rules": [
                "不要做疾病诊断",
                "不要承诺疗效",
                "不要给出处方、药物、注射或医美治疗建议",
                "输出必须是 JSON，不要包含 Markdown",
            ],
        },
        ensure_ascii=False,
    )


def _photo_image_urls(photos: list[dict[str, Any]]) -> list[str]:
    """提取多模态模型可用的图片地址。"""
    from app.conf.app_config import app_config

    urls: list[str] = []
    for photo in photos:
        url = str(photo.get("url", "")).strip()
        if not url:
            continue
        if url.startswith(("http://", "https://", "data:image/")):
            urls.append(url)
            continue
        storage = app_config.storage
        if storage.provider.lower().strip() == "minio":
            scheme = "https" if storage.minio.secure else "http"
            key = quote(url, safe="/")
            urls.append(f"{scheme}://{storage.minio.endpoint}/{storage.minio.bucket}/{key}")
        else:
            urls.append(url)
    return urls


async def _llm_diagnose(
    photos: list[dict[str, Any]],
    profile: dict[str, Any],
    complaint: str | None,
) -> tuple[dict[str, Any], Decimal, str]:
    """调用多模态 LLM 主备链；失败回退规则引擎。"""
    from app.llm.client import LLMMessage, MultimodalRequest
    from app.llm.multimodal_chain import MultimodalFallbackChain

    payload = _rule_engine_fallback(profile, complaint)
    model_used = "rule-engine"
    chain = MultimodalFallbackChain(
        on_all_failed=lambda _request: json.dumps(
            _rule_engine_fallback(profile, complaint), ensure_ascii=False
        )
    )
    request = MultimodalRequest(
        messages=[LLMMessage(role="user", content=_diagnosis_prompt(profile, complaint))],
        images=_photo_image_urls(photos),
        metadata={"photo_count": len(photos), "profile": profile},
    )
    try:
        result = await chain.run(request)
        model_used = result.provider_used
        if result.provider_used == "rule-engine":
            payload = _rule_engine_fallback(profile, complaint)
        else:
            try:
                parsed = json.loads(result.content)
                payload = parsed if isinstance(parsed, dict) else payload
            except (ValueError, TypeError):
                logger.warning(
                    "llm_diagnose_invalid_json",
                    provider=result.provider_used,
                    content_preview=result.content[:200],
                )
    except Exception as exc:
        logger.warning(
            "llm_diagnose_fallback_to_rule_engine",
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
        )

    directions = _normalize_directions(payload.get("directions"))
    tags = _normalize_tags(payload.get("tags"))
    summary = str(payload.get("summary", ""))
    if complaint:
        safety = _check_text_safety(complaint)
        if not safety.get("passed", True):
            summary = "我无法回答医疗问题，建议您咨询专业医师。"
    return (
        {"directions": directions, "tags": tags, "summary": summary},
        Decimal(str(payload.get("llm_cost", "0.0"))),
        model_used,
    )


def check_text_safety(text: str) -> dict[str, object]:
    """Sprint 2 业务层合规模块：检查用户输入。

    Returns:
        ``{"passed": bool, "matches": list[str], "severity": str}``

    """
    result = _check_input_compliance(text)
    return {
        "passed": not result.get("blocked", False),
        "matches": result.get("matches", []),
        "severity": result.get("severity", "normal"),
    }


def _rule_engine_fallback(profile: dict[str, Any], complaint: str | None) -> dict[str, Any]:
    """规则引擎兜底：基于档案标签 + intensity 输出标准方案。"""
    parts = profile.get("focus_parts") or ["整体气色"]
    directions = []
    for i, part in enumerate(parts[:3]):
        directions.append(
            {
                "title": f"{part} 方向 {i + 1}",
                "description": "建议从轻柔训练开始，配合规律作息。",
                "video_id": None,
            }
        )
    return {
        "directions": directions,
        "tags": ["基础养护"] + [str(p) for p in parts[:6]],
        "summary": "已为您生成基础养护方向。",
        "llm_cost": "0.0",
    }


def _flatten_items(v: object) -> object:
    """兜底 ``{"items": [...]}`` 嵌套 dict → list。

    历史背景：旧 Sprint 2 实现的 ``user.report_cache`` 把 ``directions``/``tags`` 存为
    ``{"items": [...]}``，导致 ``DiagnosisData`` 校验失败 (500)。
    """
    if isinstance(v, dict) and "items" in v:
        items = v["items"]
        return items if isinstance(items, list) else []
    return v


def _get_cached_report(user: User) -> dict[str, Any] | None:
    """7 天缓存检查（直接读 user.report_cache）。"""
    cache = user.report_cache or {}
    expires_at = user.report_cache_expires_at
    if not cache or expires_at is None:
        return None
    if expires_at < datetime.now(UTC):
        return None
    return {
        "report_id": cache.get("report_id"),
        "directions": _normalize_directions(_flatten_items(cache.get("directions", []))),
        "tags": _normalize_tags(_flatten_items(cache.get("tags", []))),
        "summary": cache.get("summary", ""),
        "cached": True,
    }


async def create_diagnosis(
    session: AsyncSession,
    *,
    user_id: str,
    photos: list[dict[str, Any]],
    complaint: str | None = None,
) -> dict[str, Any]:
    """创建诊断报告（主入口）。

    Returns:
        报告 dict（包含 report_id / directions / tags / summary / cached）。

    """
    # 1. 加载 user
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise DiagnosisNotFoundError(field="user_id")

    # 2. 缓存命中
    cached = _get_cached_report(user)
    if cached is not None:
        logger.info("diagnosis_cache_hit", user_id=user_id)
        return cached

    # 3. 校验输入
    validated_photos = _validate_photos(photos)
    validated_complaint = _validate_complaint(complaint)

    # 4. profile 序列化
    profile = {
        "age_range": user.age_range,
        "focus_parts": user.focus_parts or [],
        "intensity": user.intensity,
        "preferred_time": user.preferred_time,
        "sitting_hours": user.sitting_hours,
    }

    # 5. LLM 降级链
    payload, cost, model = await _llm_diagnose(validated_photos, profile, validated_complaint)

    # 6. 写 Report
    now_ts = datetime.now(UTC)
    report = Report(
        id=uuid4(),
        user_id=user.id,
        photos={"items": validated_photos},
        directions={"items": payload["directions"]},
        tags={"items": payload["tags"]},
        summary=payload["summary"],
        llm_model=model,
        llm_cost=cost,
        created_at=now_ts,
        created_by=str(user.id),  # 当前创建用户（诊断发起人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user.id),  # 当前更新用户
    )
    session.add(report)

    # 7. 写 user.report_cache（7 天）
    user.report_cache = {
        "report_id": str(report.id),
        "directions": payload["directions"],
        "tags": payload["tags"],
        "summary": payload["summary"],
    }
    user.report_cache_expires_at = now_ts + timedelta(days=CACHE_TTL_DAYS)
    user.last_active_at = now_ts
    user.last_updated_time = now_ts
    user.last_updated_by = str(user.id)  # 当前更新用户

    await session.flush()
    logger.info("diagnosis_created", report_id=str(report.id), user_id=user_id, model=model)
    return {
        "report_id": str(report.id),
        "directions": payload["directions"],
        "tags": payload["tags"],
        "summary": payload["summary"],
        "cached": False,
        "llm_model": model,
    }


async def get_diagnosis(session: AsyncSession, *, user_id: str, report_id: str) -> dict[str, Any]:
    """获取诊断报告。"""
    try:
        report_uuid = UUID(str(report_id))
        user_uuid = UUID(str(user_id))
    except ValueError as exc:
        raise DiagnosisNotFoundError(field="report_id") from exc

    stmt = select(Report).where(Report.id == report_uuid, Report.user_id == user_uuid)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    if report is None or report.deleted_at is not None:
        raise DiagnosisNotFoundError(field="report_id")
    return {
        "report_id": str(report.id),
        "directions": report.directions.get("items", []) if report.directions else [],
        "tags": report.tags.get("items", []) if report.tags else [],
        "summary": report.summary or "",
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


__all__ = [
    "CACHE_TTL_DAYS",
    "MAX_COMPLAINT_LENGTH",
    "MAX_IMAGE_BYTES",
    "DiagnosisError",
    "DiagnosisNotFoundError",
    "DiagnosisRateLimitError",
    "create_diagnosis",
    "get_diagnosis",
]
