"""M3 视频匹配算法（facts-anchor §5 权重 0.5/0.3/0.2）。"""

from __future__ import annotations

from typing import Any


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard 相似度。空集时返回 0.0。"""
    if not set_a or not set_b:
        return 0.0
    inter = set_a & set_b
    union = set_a | set_b
    return len(inter) / len(union) if union else 0.0


def _parse_tags(video_tags: object) -> set[str]:
    """视频 tags 字段（JSONB list / dict）转 set[str]。"""
    if isinstance(video_tags, list):
        return {str(t) for t in video_tags}
    if isinstance(video_tags, dict):
        return {str(k) for k in video_tags.keys()}
    return set()


def _intensity_to_num(intensity: str | None) -> int:
    """intensity（中文）→ 1-5 数字档。"""
    return {"轻柔": 1, "适中": 3, "进阶": 5}.get(intensity or "适中", 3)


def _preferred_duration_sec(preferred_time: str | None) -> int:
    """preferred_time → 推荐时长（秒）。"""
    return {"早": 5 * 60, "中": 15 * 60, "晚": 20 * 60, "不固定": 15 * 60}.get(
        preferred_time or "不固定", 15 * 60
    )


def score_video(
    video: dict[str, Any],
    report_tags: list[str] | set[str],
    *,
    intensity: str | None = "适中",
    preferred_time: str | None = "不固定",
) -> float:
    """视频匹配得分 = 0.5 * 标签 + 0.3 * 时长 + 0.2 * 难度。

    Args:
        video: 视频 dict（必须含 ``tags`` / ``duration_sec`` / ``difficulty``）。
        report_tags: 智能分析标签集合。
        intensity: 用户强度（中文 / 数字）。
        preferred_time: 用户偏好时段。

    Returns:
        0.0 ~ 1.0 之间的得分。

    """
    v_tags = _parse_tags(video.get("tags"))
    r_tags = {str(t) for t in report_tags}
    tag_score = jaccard_similarity(v_tags, r_tags)

    v_duration = int(video.get("duration_sec", 0) or 0)
    target_duration = _preferred_duration_sec(preferred_time)
    if v_duration <= 0:
        duration_score = 0.0
    else:
        # 时长差异归一化到 [0, 1]；60s 内算完全匹配，超 60s 线性衰减
        diff = abs(v_duration - target_duration)
        duration_score = max(0.0, 1.0 - diff / 60.0)

    v_difficulty = int(video.get("difficulty", 3) or 3)
    target_difficulty = _intensity_to_num(intensity)
    diff_difficulty = abs(v_difficulty - target_difficulty)
    difficulty_score = max(0.0, 1.0 - diff_difficulty / 5.0)

    return 0.5 * tag_score + 0.3 * duration_score + 0.2 * difficulty_score


def rank_videos(
    videos: list[dict[str, Any]],
    report_tags: list[str] | set[str],
    *,
    intensity: str | None = "适中",
    preferred_time: str | None = "不固定",
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """对视频按 score_video 排序。

    Returns:
        排序后的视频列表（带 ``score`` 字段）。

    """
    scored: list[dict[str, Any]] = []
    for v in videos:
        s = score_video(
            v, report_tags, intensity=intensity, preferred_time=preferred_time
        )
        scored.append({**v, "score": round(s, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    if top_k is not None:
        return scored[:top_k]
    return scored


__all__ = [
    "jaccard_similarity",
    "rank_videos",
    "score_video",
]
