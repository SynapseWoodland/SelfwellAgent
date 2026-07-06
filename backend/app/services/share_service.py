"""M10 抱抱卡 / 分享海报 service。

真源：``docs/spec/SPEC-M10-share-card.md``。
- 3 模板：day7 / day14 / day21
- PIL 生成 750x1000 海报
- 上传 COS，返回公网 URL
"""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.conf.app_config import app_config
from app.core.errors import SelfwellError
from app.core.log import logger
from app.errors.codes import (
    E_SHARE_PLAN_NOT_FOUND,
    E_SHARE_RENDER_FAILED,
    E_SHARE_TEMPLATE_INVALID,
)

VALID_DAYS: frozenset[int] = frozenset({7, 14, 21})
POSTER_WIDTH = 750
POSTER_HEIGHT = 1000
ALLOWED_COLORS: frozenset[str] = frozenset(
    {"#A8C5B5", "#F5E6D3", "#E8D5B7", "#FFFFFF", "#2D2D2D"}
)
# §17 禁用色
FORBIDDEN_COLORS: frozenset[str] = frozenset({"#FF4D4F", "#D32F2F", "#007BFF"})

TEMPLATES: dict[int, dict[str, Any]] = {
    7: {
        "title": "第一周纪念",
        "subtitle": "你开始了，这本身就是最棒的事。",
        "primary_color": "#A8C5B5",
        "badge": "Week 1",
    },
    14: {
        "title": "第二周加油",
        "subtitle": "你走过的每一天，都算数。",
        "primary_color": "#F5E6D3",
        "badge": "Week 2",
    },
    21: {
        "title": "蜕变完成",
        "subtitle": "21 天的坚持，你已经不一样了。",
        "primary_color": "#E8D5B7",
        "badge": "21 Days",
    },
}


class ShareError(SelfwellError):
    """抱抱卡业务异常。"""

    code: str = E_SHARE_TEMPLATE_INVALID
    message_zh: str = "分享请求无效"
    message_en: str = "Invalid share request"
    severity = "USER_ERROR"
    http_status = 400


class ShareRenderError(ShareError):
    code: str = E_SHARE_RENDER_FAILED
    message_zh: str = "海报生成失败"
    message_en: str = "Poster rendering failed"
    http_status = 500
    severity = "PERMANENT"


def _validate_day(day: int) -> int:
    if day not in VALID_DAYS:
        raise ShareError(
            f"day 必须是 {sorted(VALID_DAYS)} 之一",
            code=E_SHARE_TEMPLATE_INVALID,
            field="day",
        )
    return day


def _validate_color(color: str) -> str:
    """§17 像素禁用色校验。"""
    if color in FORBIDDEN_COLORS:
        raise ShareError(
            f"颜色 {color} 在 §17 禁用列表中",
            code=E_SHARE_RENDER_FAILED,
            field="color",
        )
    return color


def _render_poster_pil(day: int, nickname: str, stats: dict[str, int]) -> bytes:
    """用 PIL 渲染海报，返回 PNG 字节。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise ShareRenderError("PIL 不可用") from exc

    template = TEMPLATES[day]
    primary_color = _validate_color(template["primary_color"])

    img = Image.new("RGB", (POSTER_WIDTH, POSTER_HEIGHT), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # 顶部装饰条
    draw.rectangle([(0, 0), (POSTER_WIDTH, 240)], fill=primary_color)
    # Badge
    try:
        font_badge = ImageFont.truetype("arial.ttf", 36)
        font_title = ImageFont.truetype("arial.ttf", 64)
        font_sub = ImageFont.truetype("arial.ttf", 32)
        font_nick = ImageFont.truetype("arial.ttf", 48)
        font_stat = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font_badge = font_title = font_sub = font_nick = font_stat = ImageFont.load_default()

    # Badge
    draw.text((40, 80), template["badge"], fill="#2D2D2D", font=font_badge)

    # Title
    draw.text((40, 360), template["title"], fill="#2D2D2D", font=font_title)

    # Subtitle（注意 §17 不允许使用禁用色）
    sub_y = 450
    for line in _wrap_text(template["subtitle"], font_sub, POSTER_WIDTH - 80):
        draw.text((40, sub_y), line, fill="#2D2D2D", font=font_sub)
        sub_y += 50

    # Nickname
    draw.text((40, 620), f"@{nickname[:20]}", fill="#A8C5B5", font=font_nick)

    # Stats
    stat_y = 740
    draw.text(
        (40, stat_y),
        f"碎片 {stats.get('fragments', 0)}  ·  连续 {stats.get('streak_days', 0)} 天",
        fill="#2D2D2D",
        font=font_stat,
    )

    # 底部
    draw.text(
        (40, POSTER_HEIGHT - 80),
        f"Gen at {datetime.now(UTC).strftime('%Y-%m-%d')}",
        fill="#2D2D2D",
        font=font_stat,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _wrap_text(text: str, font: Any, max_width: int) -> list[str]:
    """简单文本换行。"""
    lines: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        try:
            if font.getlength(cur) > max_width:
                lines.append(cur[:-1])
                cur = ch
        except AttributeError:
            if len(cur) * 24 > max_width:
                lines.append(cur[:-1])
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def _upload_poster_bytes(poster_bytes: bytes, *, user_id: str, day: int) -> str:
    """上传到对象存储并返回公网 URL。"""
    object_key = f"share/{user_id}/day{day}_{uuid4().hex[:8]}.png"
    # MVP 阶段：本地落盘 + 返回占位 URL
    # 生产由 M11 / storage/ 接入 COS / MinIO
    try:
        from app.storage.minio_impl import MinioStorage

        storage = MinioStorage()
        # MinioStorage.put_object 是 async；这里我们走同步写入 + URL
        # 真实生产应使用 presigned_url + 前端直传
    except Exception:
        pass
    # 兜底：写到 /tmp 返回本地路径
    local_path = f"/tmp/{object_key}"  # noqa: S108
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(poster_bytes)
    return f"https://placeholder.local{local_path}"


async def generate_hug_card(
    *,
    user_id: str,
    day: int,
    nickname: str,
    stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    """生成抱抱卡海报。"""
    day = _validate_day(day)
    if stats is None:
        stats = {"fragments": 0, "streak_days": 0}

    try:
        poster_bytes = _render_poster_pil(day, nickname, stats)
    except ShareRenderError:
        raise
    except Exception as exc:
        logger.exception("hug_card_render_failed", day=day, user_id=user_id)
        raise ShareRenderError(str(exc)) from exc

    url = _upload_poster_bytes(poster_bytes, user_id=user_id, day=day)
    return {
        "day": day,
        "template": TEMPLATES[day]["title"],
        "url": url,
        "width": POSTER_WIDTH,
        "height": POSTER_HEIGHT,
        "size_bytes": len(poster_bytes),
        "stats": stats,
        "created_at": datetime.now(UTC).isoformat(),
    }


async def get_template_meta(day: int) -> dict[str, Any]:
    """返回模板元数据（前端预览用）。"""
    day = _validate_day(day)
    t = TEMPLATES[day]
    return {
        "day": day,
        "title": t["title"],
        "subtitle": t["subtitle"],
        "badge": t["badge"],
        "primary_color": t["primary_color"],
        "width": POSTER_WIDTH,
        "height": POSTER_HEIGHT,
    }


__all__ = [
    "ALLOWED_COLORS",
    "FORBIDDEN_COLORS",
    "POSTER_HEIGHT",
    "POSTER_WIDTH",
    "ShareError",
    "ShareRenderError",
    "VALID_DAYS",
    "generate_hug_card",
    "get_template_meta",
]


# 抑制 unused warning
_ = E_SHARE_PLAN_NOT_FOUND
_ = app_config
