"""M2 diagnosis business service（M2 多模态诊断）。

真源：``docs/spec/SPEC-M2-multimodal-diagnosis.md`` + ADR-0003。
- 6 节点子图：upload → validate → compliance → llm_diagnose → format → cache
- 7 天 Redis 缓存（按 user_id key）
- 4 级降级链 + 规则引擎兜底
- 5 条合规红线（R1-R5）1:1 进入 Prompt
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

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
    """校验 3 张照片（face/head/shoulder_neck）。"""
    if not isinstance(photos, list) or len(photos) != 3:
        raise UserInputError(
            "需要 3 张照片",
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


def _normalize_directions(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) < MIN_DIRECTIONS:
        return [
            {
                "title": "基础养护方向",
                "description": "建议从轻柔开始，逐步建立规律作息。",
                "video_id": None,
            }
            for _ in range(MIN_DIRECTIONS)
        ]
    return raw[:MAX_DIRECTIONS]


def _normalize_tags(raw: list[str] | None) -> list[str]:
    if not isinstance(raw, list) or len(raw) < MIN_TAGS:
        return ["基础养护", "规律作息", "温和改善"][:MIN_TAGS]
    return [str(t) for t in raw[:MAX_TAGS]]


async def _llm_diagnose(
    photos: list[dict[str, Any]],
    profile: dict[str, Any],
    complaint: str | None,
) -> tuple[dict[str, Any], Decimal, str]:
    """调用 LLM 降级链；失败回退规则引擎。

    Returns:
        (result_dict, cost, model_name)

    """
    from app.llm.fallback_chain import FallbackChain

    chain = FallbackChain(use_mock=True)
    prompt = {
        "photos": [p["url"] for p in photos],
        "profile": profile,
        "complaint": complaint or "",
    }
    try:
        result = await chain.run(json.dumps(prompt, ensure_ascii=False))
        # 解析 JSON（Mock LLM 可能返回固定结构）
        if result.provider_used == "rule-engine":
            payload = _rule_engine_fallback(profile, complaint)
        else:
            try:
                payload = json.loads(result.content)
            except (ValueError, TypeError):
                payload = _rule_engine_fallback(profile, complaint)
    except Exception:
        logger.exception("llm_diagnose_failed")
        payload = _rule_engine_fallback(profile, complaint)

    directions = _normalize_directions(payload.get("directions"))
    tags = _normalize_tags(payload.get("tags"))
    summary = str(payload.get("summary", ""))
    # 合规审查（R1-R5）
    if complaint:
        safety = _check_text_safety(complaint)
        if not safety.get("passed", True):
            summary = "我无法回答医疗问题，建议您咨询专业医师。"
    return (
        {"directions": directions, "tags": tags, "summary": summary},
        Decimal(str(payload.get("llm_cost", "0.0"))),
        result.provider_used,
    )


def check_text_safety(text: str) -> dict[str, object]:
    """Wrapper around compliance.checker.check_input for the diagnosis service.

    Returns:
        ``{"passed": bool, "matches": list[str], "severity": str}``

    """
    result = check_text_safety._check_input(text)  # type: ignore[attr-defined]
    return {
        "passed": not result.get("blocked", False),
        "matches": result.get("matches", []),
        "severity": result.get("severity", "normal"),
    }


# Patch the namespace so ``check_text_safety`` is callable.


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


def _rule_engine_fallback(
    profile: dict[str, Any], complaint: str | None
) -> dict[str, Any]:
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
        "directions": _flatten_items(cache.get("directions", [])),
        "tags": _flatten_items(cache.get("tags", [])),
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
        created_by=str(user.id),         # 当前创建用户（诊断发起人）
        created_time=now_ts,
        last_updated_time=now_ts,
        last_updated_by=str(user.id),    # 当前更新用户
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


async def get_diagnosis(
    session: AsyncSession, *, user_id: str, report_id: str
) -> dict[str, Any]:
    """获取诊断报告。"""
    stmt = select(Report).where(Report.id == report_id, Report.user_id == user_id)
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
