"""M2 diagnosis business service（M2 多模态诊断）。

真源：``docs/spec/SPEC-M2-multimodal-diagnosis.md`` + ADR-0003。
- 6 节点子图：upload → validate → compliance → llm_diagnose → format → cache
- 7 天 Redis 缓存（按 user_id key）
- 多模态主备链 + 规则引擎兜底
- 5 条合规红线（R1-R5）1:1 进入 Prompt

PR-A2（async pipeline · 2026-07-08）增量：
- 拆 ``_llm_diagnose`` 为 ``_invoke_llm_structured``（LLM 调用 + missing_note 拼接），
  同步路径仍用 ``_llm_diagnose`` 薄包装调用；不改 PR-A3 既有测试。
- 新增 ``stream_diagnose``：阶段式推送 ``JobEvent(kind="stage")``，
  最终 ``done``，异常 ``error``。
- 新增 ``run_diagnosis_job``：被 router 用 ``asyncio.create_task`` 启动的入参包装。
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.job_state import JobStateStore
from app.core.log import logger
from app.db.models.report import Report
from app.db.models.user import User
from app.errors.codes import (
    E_DIAGNOSIS_COMPLAINT_TOO_LONG,
    E_DIAGNOSIS_FACE_REQUIRED,
    E_DIAGNOSIS_IMAGE_FORMAT_UNSUPPORTED,
    E_DIAGNOSIS_IMAGE_TOO_LARGE,
    E_DIAGNOSIS_INVALID_INPUT,
    E_DIAGNOSIS_NOT_FOUND,
    E_DIAGNOSIS_PIPELINE_FAILED,
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


def _resolve_object_key_to_url(object_key: str) -> str:
    """把 ``object_key`` 解析成可访问 URL（用于 ``object_key`` alias 兼容）。

    实现：调 ``MinioStorage.presigned_url`` 生成临时 GET URL。
    若对象存储未配置或不可用，回退为 ``{endpoint}/{bucket}/{key}`` 公开读 URL。

    Args:
        object_key: 形如 ``diagnosis/u-xxx/uuid.jpg`` 的对象 key。

    Returns:
        可访问的 URL 字符串。

    """
    try:
        from app.conf.app_config import app_config
        from app.storage.factory import get_storage

        storage = get_storage()
        # GET presigned（put presigned 不能直接给到 LLM 读）
        try:
            return storage.presigned_get_url(object_key, expires_sec=3600)
        except AttributeError:
            # 兼容旧实现：某些存储未提供 presigned_get_url，临时退回公开 URL
            storage_cfg = app_config.storage
            scheme = "https" if storage_cfg.minio.secure else "http"
            return f"{scheme}://{storage_cfg.minio.endpoint}/{storage_cfg.minio.bucket}/{object_key}"
    except Exception:
        # 对象存储未配置 / 不可用：退回 MinIO 公开读 URL（开发态可用）
        from app.conf.app_config import app_config

        storage_cfg = app_config.storage
        scheme = "https" if storage_cfg.minio.secure else "http"
        return f"{scheme}://{storage_cfg.minio.endpoint}/{storage_cfg.minio.bucket}/{object_key}"


def _validate_photos(photos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """校验前端 1-3 张照片输入（face 必含）。

    数量规则（MVP A 场景 · Sprint 2026-07-08）：
    - 接受 ``1 ≤ len(photos) ≤ 3``，允许用户跳过 head / shoulder_neck 等可选视角。
    - 至少 1 张 ``body_part == "face"`` 必传（面部是诊断的核心输入）。
    - 不足 3 张时，调用方应在 LLM 提示词末尾追加 ``[NOTE] 缺失 N 张图片 (body_parts 缺失: [...])``，
      由 ``_llm_diagnose`` 自动拼接。

    N-1 兼容：
    - 同时接受 ``url`` 和 ``object_key`` 两种字段（首选 ``url``，缺失则用
      ``object_key`` 通过 ``_resolve_object_key_to_url`` 解析成 presigned URL）。
    - 历史背景：Sprint 2026-07-08 前端 diagnosis-upload helper
      (``apps/mp-selfwell/miniprogram/utils/upload-helper.ts``) 发
      ``{object_key, body_part, format, size_bytes}``，旧 service 读 ``url``
      必然 400 → 前端走 mock，永远到不了 LLM。
    - 前端切到 ``url`` 字段后（待 PM 排期），可删除 ``object_key`` 兼容分支
      （同时 ``_resolve_object_key_to_url`` 可保留作为 ObjectKey 解析工具）。

    字段语义：
    - ``url``：首选字段，公开可访问 URL。
    - ``object_key``：alias；用于调 ``MinioStorage.presigned_get_url`` 构造临时访问 URL。
    - ``body_part``：face | head | shoulder_neck。
    - ``format``：jpg | png | webp | heic。
    - ``size_bytes``：字节。

    Args:
        photos: 1-3 张照片 dict。

    Returns:
        校验后的 photos 列表（每项包含 ``url`` 与 ``object_key``，以便下游 LLM/缓存
        都能正确处理）。

    Raises:
        UserInputError: 数量错 / 字段缺失 / body_part 非法 / 缺少 face。
        DiagnosisError: 格式不支持 / 体积过大。

    """
    if not isinstance(photos, list) or not (1 <= len(photos) <= 3):
        raise UserInputError(
            "需要 1-3 张照片",
            code=E_DIAGNOSIS_INVALID_INPUT,
            field="photos",
        )
    body_parts_seen: set[str] = set()
    for photo in photos:
        if isinstance(photo, dict):
            bp = photo.get("body_part")
            if isinstance(bp, str):
                body_parts_seen.add(bp)
    if "face" not in body_parts_seen:
        raise UserInputError(
            "至少需要 1 张面部照片（body_part=face）",
            code=E_DIAGNOSIS_FACE_REQUIRED,
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
        object_key = photo.get("object_key")
        body_part = photo.get("body_part")
        size = photo.get("size_bytes", 0)
        fmt = photo.get("format", "jpg").lower()
        if not url and not object_key:
            raise UserInputError(
                f"第 {idx + 1} 张照片 url / object_key 缺失",
                code=E_DIAGNOSIS_INVALID_INPUT,
                field=f"photos[{idx}]",
            )
        # 兼容：若只有 object_key，把它解析成可访问 URL
        if not url:
            url = _resolve_object_key_to_url(str(object_key))
        if not isinstance(url, str):
            raise UserInputError(
                f"第 {idx + 1} 张照片 url 非字符串",
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
        validated.append(
            {
                "url": url,
                "object_key": object_key or url,
                "body_part": body_part,
                "format": fmt,
                "size_bytes": size,
            }
        )
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


async def _photo_image_urls(photos: list[dict[str, Any]]) -> list[str]:
    """提取多模态模型可用的图片地址。

    V5.2.1-PR2 T14：改调 ``_photo_urls.build_photo_urls`` 公共 helper，
    消除内联实现（保留此函数作为薄壳，行为不变）。
    """
    from app.services._photo_urls import build_photo_urls

    return await build_photo_urls(photos)


async def _invoke_llm_structured(
    photos: list[dict[str, Any]],
    profile: dict[str, Any],
    complaint: str | None,
) -> dict[str, Any]:
    """调用多模态 LLM（structured_llm），失败回退到规则引擎。

    Returns:
        ``{"directions": list[dict], "tags": list[str], "summary": str,
           "llm_cost": str, "model": str}`` —— 字段供 service / stream 路径共用。
        LLM 成功时 ``model`` = multimodal 模型名；失败时 ``model`` = ``"rule-engine"``。

    Note:
        ``missing_parts`` 计算与 PR-A3 引入的 ``[NOTE] 缺失 N 张图片 ...`` 文案
        **完全一致**；同步 / stream 两条路径共用同一段逻辑，保证行为稳定。

    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.llm import multimodal_llm
    from app.llm.schemas import DiagnosisOutput

    default_payload = _rule_engine_fallback(profile, complaint)
    payload = default_payload
    model = "rule-engine"

    image_urls = await _photo_image_urls(photos)
    logger.info(
        "invoke_llm_structured_start",
        photo_count=len(photos),
        image_url_count=len(image_urls),
        profile_keys=list(profile.keys()),
    )
    complaint_text = complaint or ""

    # MVP A 场景：若 < 3 张照片，提示 LLM 缺失哪些视角，让模型在生成建议时显式标注。
    missing_parts: list[str] = []
    expected_parts = ("face", "head", "shoulder_neck")
    seen_parts = {
        str(p.get("body_part"))
        for p in photos
        if isinstance(p, dict) and p.get("body_part")
    }
    for part in expected_parts:
        if part not in seen_parts:
            missing_parts.append(part)
    missing_note = ""
    if len(photos) < 3 and missing_parts:
        missing_note = (
            f"\n[NOTE] 缺失 {3 - len(photos)} 张图片 "
            f"(body_parts 缺失: {missing_parts})"
        )

    # ── 多模态消息（image blocks 内联在 HumanMessage content 中）───────────────────
    system_text = (
        "你是 Selfwell 智能管家，基于用户照片和档案生成非医疗性质的基础养护建议。\n"
        "安全规则：\n"
        "1. 不要做疾病诊断\n"
        "2. 不要承诺疗效\n"
        "3. 不要给出处方、药物、注射或医美治疗建议\n"
        "4. 只输出 JSON，不要包含 Markdown 或其他文字\n"
    )
    user_text = (  # noqa: UP032  —— 保留 verbatim：与 PR-A3 LLM prompt 1:1 一致（含 JSON 转义）
        "用户档案：{profile}\n"
        "用户主诉：{complaint}\n"
        "请生成 JSON，格式如下：\n"
        "{{\n"
        '  "directions": [{{"title": "string", "description": "string", "video_id": "string|null"}}],\n'  # noqa: E501
        '  "tags": ["string"],\n'
        '  "summary": "string"\n'
        "}}{missing_note}"
    ).format(profile=profile, complaint=complaint_text, missing_note=missing_note)

    content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    content.extend(
        {"type": "image_url", "image_url": {"url": u}} for u in image_urls
    )
    messages = [SystemMessage(content=system_text), HumanMessage(content=content)]

    # ── Chain：structured_llm 直接调用 messages ─────────────────────────────────
    structured_llm = multimodal_llm.with_structured_output(DiagnosisOutput)

    # Phase 4 批次 4：LLM 调用次数 + 耗时 + 成本 一次性埋点
    _llm_start = time.perf_counter()
    _llm_outcome = "ok"
    try:
        result = await structured_llm.ainvoke(messages)
        model = getattr(multimodal_llm, "model", "multimodal")
        payload = {
            "directions": [d.model_dump() for d in result.directions],
            "tags": result.tags,
            "summary": result.summary,
            "llm_cost": "0",
        }
    except Exception as exc:
        # 完整错误信息：traceback + 完整消息
        import traceback as _tb

        error_details = "".join(_tb.format_exception(type(exc), exc, exc.__traceback__))
        logger.warning(
            "llm_diagnose_fallback_to_rule_engine",
            error_type=type(exc).__name__,
            error_message=str(exc),
            error_details=error_details[:2000],  # 完整 traceback 限制 2000 字符
        )
        payload = default_payload
        model = "rule-engine"
        _llm_outcome = "exception"

    result_directions = _normalize_directions(payload.get("directions"))
    logger.info(
        "invoke_llm_structured_done",
        model=model,
        directions_count=len(result_directions),
        tags_count=len(payload.get("tags", [])),
    )

    # V5.2.1-PR3 T16：上报 llm_cost 到 Prometheus LLM_COST_YUAN_TOTAL
    raw_cost = payload.get("llm_cost", "0.0")
    try:
        cost_float = float(raw_cost)
    except (TypeError, ValueError):
        cost_float = 0.0
    try:
        from app.core.metrics import LLM_COST_YUAN_TOTAL
        LLM_COST_YUAN_TOTAL.labels(model=model, intent="vision_diagnose").inc(cost_float)
    except Exception as exc:
        # 指标上报失败不应阻断主流程
        logger.warning(
            "llm_cost_metric_inc_failed",
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
        )

    # Phase 4 批次 4：补 LLM_CALLS_TOTAL + LLM_LATENCY_SECONDS / VISION_LATENCY_SECONDS
    # 这些指标之前定义了但没埋，批次 2 的 llm_cost=0 残留就是缺这块导致的。
    try:
        _elapsed = time.perf_counter() - _llm_start
        from app.core.metrics import (
            LLM_CALLS_TOTAL,
            LLM_LATENCY_SECONDS,
            VISION_LATENCY_SECONDS,
        )

        # is_mock = True 当 fallback 到 rule-engine；保留 label 兼容性
        LLM_CALLS_TOTAL.labels(
            model=model,
            intent="vision_diagnose",
            is_mock=str(model == "rule-engine").lower(),
        ).inc()
        if model == "rule-engine":
            # rule-engine 走 fallback，不算真实 vision LLM 延迟
            LLM_LATENCY_SECONDS.labels(model=model, intent="vision_diagnose").observe(_elapsed)
        else:
            VISION_LATENCY_SECONDS.labels(model=model, outcome=_llm_outcome).observe(_elapsed)
            LLM_LATENCY_SECONDS.labels(model=model, intent="vision_diagnose").observe(_elapsed)
    except Exception as exc:
        logger.warning(
            "llm_metric_observe_failed",
            error_type=type(exc).__name__,
            error_message=str(exc)[:200],
        )

    return {
        "directions": _normalize_directions(payload.get("directions")),
        "tags": _normalize_tags(payload.get("tags")),
        "summary": str(payload.get("summary", "")),
        "llm_cost": str(cost_float),
        "model": model,
    }


async def _llm_diagnose(
    photos: list[dict[str, Any]],
    profile: dict[str, Any],
    complaint: str | None,
) -> tuple[dict[str, Any], Decimal, str]:
    """兼容旧契约的薄包装（PR-A3 测试 + 同步 POST 路径沿用）。

    Returns:
        ``(payload, llm_cost_decimal, model_name)``
        payload 字段与 ``_invoke_llm_structured()`` 返回值去掉 ``llm_cost`` / ``model``。

    Note:
        主叫方（``create_diagnosis`` 同步路径）已 hardcode 期望此签名，
        本函数只做"转调 + summary 安全检查 + 字段裁剪"，**不**再做 LLM 调用。

    """
    raw = await _invoke_llm_structured(photos, profile, complaint)
    summary = raw["summary"]
    if complaint:
        safety = _check_text_safety(complaint)
        if not safety.get("passed", True):
            summary = "我无法回答医疗问题，建议您咨询专业医师。"
    return (
        {"directions": raw["directions"], "tags": raw["tags"], "summary": summary},
        Decimal(raw["llm_cost"] or "0.0"),
        raw["model"],
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
    """规则引擎兜底：缺料时不返假报告（V5.2.1-PR4 T22 + F4）.

    V5.2.1 §3.10 旧版返 directions[] 含形如 part 方向 N 的垃圾标题——前端识别不出
    "这是 fallback 不是 LLM 真实报告"，用户看到"脸 方向 1"这种长得像报告但不是报告的内容。

    PR4 F4 改：directions/tags 留空 + is_fallback=true + fallback_reason="资料不足"，前端
    识别后不渲染 report card，转引导用户补料（参 docs/api/sse-events.md §5.5）。

    Returns:
    dict 含 is_fallback=True、fallback_reason、空 directions/tags、引导 summary。

    """
    return {
        "is_fallback": True,
        "fallback_reason": "资料不足",
        "directions": [],
        "tags": [],
        "summary": "请先补充档案与图片后再进行智能分析。",
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

    Note:
        本函数是 **同步降级路径**（per ADR-0004），主要用于：
        - 老客户端 / SDK / 内部脚本兼容
        - SSE 不可用时的兜底（前端 POST 等结果超时降级）
        生产主路径请改走 ``POST /diagnosis?async=true`` →
        ``GET /diagnosis/jobs/{job_id}/stream``（PR-A2）。

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
    # cached = _get_cached_report(user)
    # if cached is not None:
    #     logger.info("diagnosis_cache_hit", user_id=user_id)
    #     return cached

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


# ─────────────────────────────────────────────────────────────────────────────
# PR-A2 · SSE 真 pipeline 推送（plan §4.2 + §6.1 + JobStateStore）
# ─────────────────────────────────────────────────────────────────────────────
_COPY_FILE: Path = Path(__file__).resolve().parents[1] / "conf" / "assistant_copy.yaml"


@lru_cache(maxsize=1)
def _load_assistant_copy() -> dict[str, Any]:
    """懒加载 ``assistant_copy.yaml``；lru_cache 一次性。

    失败兜底返回 ``{}``（不抛 —— 启动期不允许因 yaml 文件不在而拒服务）。
    """
    try:
        return yaml.safe_load(_COPY_FILE.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}


def _diag_phase_message(stage: str) -> str:
    """获取阶段中文文案（``assistant_copy.yaml`` §三 ``diag_phase.<stage>``）。

    Fallback：key 缺失或 yaml 加载失败 → 返回 ``stage`` 原 key（与既有
    ``utils/sse-stage.ts`` 前端契约兼容，前端按英文 key 显示）。
    """
    raw = _load_assistant_copy()
    phase = raw.get("diag_phase") or {}
    if isinstance(phase, dict):
        msg = phase.get(stage)
        if isinstance(msg, str) and msg:
            return msg
    return stage


# Stage 顺序（plan §4.2）。``stage`` 是 SSE 事件名，``percent`` 给前端进度条参考。
_STAGE_SEQUENCE: tuple[tuple[str, int], ...] = (
    ("connected", 0),
    ("preprocess", 15),
    ("analyzing", 45),
    ("suggestion", 75),
    ("ready", 100),
)


@dataclass(slots=True, frozen=True)
class StreamDiagnoseInputs:
    """``stream_diagnose`` 入参 bundle（避免超 PLR0913 5 参限制）。"""

    photos: list[dict[str, Any]]
    complaint: str | None
    user_id: str
    report_id: str
    job_id: str
    profile: dict[str, Any]


@dataclass(slots=True)
class DiagnosisJobInputs:
    """``run_diagnosis_job`` 入参 bundle（除 ``job_id`` 外的所有入参 + db factory）。"""

    photos: list[dict[str, Any]]
    complaint: str | None
    user_id: str
    report_id: str
    db_factory: Callable[[], Awaitable[AsyncSession]]
    store: JobStateStore


async def _emit_stage(
    store: JobStateStore,
    job_id: str,
    *,
    stage: str,
    percent: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """向 ``store`` 推一条 stage 事件，并在事件循环中让步一次（让消费者能立即拉走）。

    Note:
        ``append_event`` 在 ``JobStateStore`` 接口里是 **sync**（PR-A1）；
        本辅助函数只是包一层 await ``asyncio.sleep(0)`` 让出事件循环。

    """
    payload: dict[str, Any] = {
        "stage": stage,
        "percent": percent,
        "message": _diag_phase_message(stage),
        "ok": True,
    }
    if extra:
        payload.update(extra)
    store.append_event(job_id, {"kind": "stage", **payload})
    await asyncio.sleep(0)


async def _emit_done(
    store: JobStateStore, job_id: str, *, report_id: str
) -> None:
    """向 ``store`` 推 done 事件（包含 report_id，stream 端点回送给前端）。"""
    store.append_event(
        job_id,
        {"kind": "done", "report_id": report_id, "message": _diag_phase_message("ready")},
    )


async def _emit_error(
    store: JobStateStore,
    job_id: str,
    *,
    code: str,
    message_zh: str,
    stage: str,
) -> None:
    """向 ``store`` 推 error 事件（异常收尾；不抛 —— 调用方决定是否 re-raise）。"""
    store.append_event(
        job_id,
        {
            "kind": "error",
            "code": code,
            "message_zh": message_zh,
            "stage": stage,
        },
    )


async def _persist_report_ready(
    db: AsyncSession,
    *,
    report_id: str,
    user_id: str,
    validated_photos: list[dict[str, Any]],
    llm_output: dict[str, Any],
) -> None:
    """把 LLM 输出落库到 Report 行。

    设计：
    - Router 在 ``POST ?async=true`` 时已 INSERT status='queued' 行并 commit；
    - 这里 ``SELECT`` 后 UPDATE ``status='ready'`` + LLM 三个字段；
    - 兜底分支：若 SELECT 为 None（理论不应发生），INSERT 一条 ready 行，避免 SSE 阻塞。
    """
    report_uuid = UUID(str(report_id))
    stmt = select(Report).where(Report.id == report_uuid)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    now_ts = datetime.now(UTC)
    if report is None:
        try:
            user_uuid = UUID(str(user_id))
        except ValueError:
            user_uuid = uuid4()
        report = Report(
            id=report_uuid,
            user_id=user_uuid,
            photos={"items": validated_photos},
            directions={"items": llm_output["directions"]},
            tags={"items": llm_output["tags"]},
            summary=llm_output["summary"],
            llm_model=llm_output["model"],
            llm_cost=Decimal(llm_output["llm_cost"] or "0.0"),
            status="ready",
            created_at=now_ts,
            created_by=str(user_id),
            created_time=now_ts,
            last_updated_time=now_ts,
            last_updated_by=str(user_id),
        )
        db.add(report)
    else:
        report.directions = {"items": llm_output["directions"]}
        report.tags = {"items": llm_output["tags"]}
        report.summary = llm_output["summary"]
        report.llm_model = llm_output["model"]
        report.llm_cost = Decimal(llm_output["llm_cost"] or "0.0")
        report.status = "ready"
        report.last_updated_time = now_ts
        report.last_updated_by = str(user_id)
    await db.flush()


async def stream_diagnose(
    inputs: StreamDiagnoseInputs,
    *,
    store: JobStateStore,
    db: AsyncSession,
) -> None:
    """按阶段执行诊断 pipeline，并逐条 ``JobEvent`` 推给 ``store``。

    阶段顺序（plan §4.2）：
        connected(0) → preprocess(15) → analyzing(45) → suggestion(75) → ready(100) → done。

    Returns:
        ``None``；成功时发出 5 条 stage 事件 + 1 条 done 事件，失败时追加 1 条 error。

    Raises:
        Exception: 内部 LLM 异常 / DB 异常会发出 error 事件后 **re-raise**
            （router 侧可记 traceback；SSE 消费者已经看到 error）。

    Note:
        ``profile`` 由 ``run_diagnosis_job`` 提前从 user 档案读取后传入；
        本函数不直接读 user，避免 SSE consumer 持有 DB session 的隐式耦合。

    """
    photos = inputs.photos
    complaint = inputs.complaint
    user_id = inputs.user_id
    report_id = inputs.report_id
    job_id = inputs.job_id
    profile = inputs.profile
    current_stage = "connected"

    async def _on_error(exc: Exception) -> None:
        await _emit_error(
            store,
            job_id,
            code=E_DIAGNOSIS_PIPELINE_FAILED,
            message_zh="诊断失败，请稍后重试",
            stage=current_stage,
        )

    try:
        # ── 1. 校验照片（复用 PR-A3 改过的 1-3 + face 校验）──────────────────────
        validated_photos = _validate_photos(photos)
        validated_complaint = _validate_complaint(complaint)

        # ── 2. 阶段事件：connected → preprocess → analyzing ───────────────────────
        await _emit_stage(store, job_id, stage="connected", percent=0)
        current_stage = "preprocess"
        await _emit_stage(store, job_id, stage="preprocess", percent=15)
        current_stage = "analyzing"
        await _emit_stage(store, job_id, stage="analyzing", percent=45)
        current_stage = "suggestion"
        await _emit_stage(store, job_id, stage="suggestion", percent=75)

        # ── 3. 调 LLM（shared helper，复用 PR-A3 missing_parts 逻辑）──────────────
        llm_output = await _invoke_llm_structured(
            validated_photos, profile, validated_complaint
        )

        # ── 4. 持久化 Report（status='ready' + 新的 directions/tags/summary）──────
        # Router 侧已在 POST ?async=true 时创建好 status='queued' 的 Report 行并 commit；
        # 这里 SELECT 出来更新其 status + 三个 LLM 字段，避免重复 INSERT。
        current_stage = "ready"
        await _persist_report_ready(
            db,
            report_id=report_id,
            user_id=user_id,
            validated_photos=validated_photos,
            llm_output=llm_output,
        )

        # ── 5. 推送 ready + done 事件（report_id 用入参，便于 router 提前创建 row）
        await _emit_stage(
            store,
            job_id,
            stage="ready",
            percent=100,
            extra={"report_id": report_id},
        )
        await _emit_done(store, job_id, report_id=report_id)

        logger.info(
            "stream_diagnose_done",
            job_id=job_id,
            report_id=report_id,
            user_id=user_id,
            model=llm_output["model"],
        )
    except Exception as exc:
        logger.exception(
            "stream_diagnose_failed",
            job_id=job_id,
            stage=current_stage,
            error_type=type(exc).__name__,
        )
        try:
            await _on_error(exc)
        except Exception:
            logger.exception("stream_diagnose_emit_error_failed", job_id=job_id)
        raise


async def run_diagnosis_job(
    job_id: str,
    inputs: DiagnosisJobInputs,
) -> None:
    """Router 层用 ``asyncio.create_task`` 启动的入口。

    1. 通过 ``inputs.db_factory`` **新建**一个 ``AsyncSession``（不要复用请求 scope），
       pipeline 跑完后统一 ``aclose``。
    2. 从 user 档案读 profile 后调 ``stream_diagnose``。
    3. 异常已由 ``stream_diagnose`` 内部 ``error`` 事件兜底；本函数记录日志，
       不再 re-raise（asyncio.create_task 默认不吞异常，会被 log 抓 traceback）。

    Note:
        ``create_task`` 会拿到本 coroutine 返回的 None；调用方无需 await。

    """
    user_id = inputs.user_id
    report_id = inputs.report_id
    store = inputs.store
    log = logger.bind(job_id=job_id, user_id=user_id, report_id=report_id)
    log.info("diagnosis_job_started")
    try:
        db = await inputs.db_factory()
        async with db:
            # ── 读 user 档案（与同步 ``create_diagnosis`` 行为一致）─────────────
            try:
                user_uuid = UUID(str(user_id))
            except ValueError:
                user_uuid = uuid4()
            stmt = select(User).where(User.id == user_uuid)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                # router 已 create_job(user_id=...) 持有 user；这里拿不到说明数据不一致
                # —— 兜底用空 profile，让 LLM 仍能给出建议
                profile: dict[str, Any] = {}
            else:
                profile = {
                    "age_range": user.age_range,
                    "focus_parts": user.focus_parts or [],
                    "intensity": user.intensity,
                    "preferred_time": user.preferred_time,
                    "sitting_hours": user.sitting_hours,
                }
            await stream_diagnose(
                StreamDiagnoseInputs(
                    photos=inputs.photos,
                    complaint=inputs.complaint,
                    user_id=user_id,
                    report_id=report_id,
                    job_id=job_id,
                    profile=profile,
                ),
                store=store,
                db=db,
            )
        log.info("diagnosis_job_done")
    except Exception:
        # stream_diagnose 已经 emit error 事件；这里只打 traceback
        log.exception("diagnosis_job_crashed")
        try:
            store.update_status(job_id, "failed")
        except Exception:
            log.exception("diagnosis_job_failed_status_update")


__all__ = [
    "CACHE_TTL_DAYS",
    "MAX_COMPLAINT_LENGTH",
    "MAX_IMAGE_BYTES",
    "DiagnosisError",
    "DiagnosisJobInputs",
    "DiagnosisNotFoundError",
    "DiagnosisRateLimitError",
    "StreamDiagnoseInputs",
    "create_diagnosis",
    "get_diagnosis",
    "run_diagnosis_job",
    "stream_diagnose",
]
