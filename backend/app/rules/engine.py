"""硬规则解释器（Sprint 0 骨架，纯 Python）。

约定：
- 不引入 OPA / DSL 引擎（保持轻量）
- 仅支持 ``weight`` 类型规则（facts-anchor §5 视频匹配算法）
- 输入：候选视频集合 + 用户偏好；输出：按 score 降序的 Top-N 视频
- 公式：``score(video) = 0.5 * 标签匹配度 + 0.3 * 时长适配度 + 0.2 * 难度适配度``
"""

from __future__ import annotations

from typing import Any

from app.rules.loader import load_rule


# ─────────────────────────────────────────────────────────────────────────────
# §一 评分原语
# ─────────────────────────────────────────────────────────────────────────────
def _jaccard(a: set[str], b: set[str]) -> float:
    """标签 Jaccard 系数。空集 → 0.0。"""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _duration_match(video_duration_sec: int, user_pref_sec: int) -> float:
    """时长适配度：``1 - |video - pref| / 60``，clamp 至 [0, 1]。"""
    diff = abs(video_duration_sec - user_pref_sec)
    score = 1.0 - (diff / 60.0)
    return max(0.0, min(1.0, score))


def _difficulty_match(video_difficulty: int, user_intensity: int) -> float:
    """难度适配度：``1 - |video - user| / 5``，clamp 至 [0, 1]。"""
    diff = abs(video_difficulty - user_intensity)
    score = 1.0 - (diff / 5.0)
    return max(0.0, min(1.0, score))


# ─────────────────────────────────────────────────────────────────────────────
# §二 视频匹配 scoring（核心 API）
# ─────────────────────────────────────────────────────────────────────────────
def score_video(
    video: dict[str, Any],
    *,
    user_tags: set[str],
    user_pref_duration_sec: int,
    user_intensity: int,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> float:
    """计算单个视频的匹配分。

    Args:
        video: 视频 dict；要求含 ``tags`` (Iterable[str]) + ``duration_sec`` + ``difficulty``。
        user_tags: 用户偏好标签集合（如 ``{'脸', '肩颈'}``）。
        user_pref_duration_sec: 用户偏好的视频时长（秒）。
        user_intensity: 用户强度等级（1-5，对应 ``轻柔/适中/进阶`` 映射）。
        weights: ``(w_tag, w_duration, w_difficulty)`` 元组。

    Returns:
        float ∈ [0.0, 1.0]

    """
    video_tags = set(video.get("tags") or [])
    s_tag = _jaccard(video_tags, user_tags)
    s_dur = _duration_match(int(video.get("duration_sec") or 0), user_pref_duration_sec)
    s_diff = _difficulty_match(int(video.get("difficulty") or 1), user_intensity)
    w_t, w_d, w_f = weights
    return w_t * s_tag + w_d * s_dur + w_f * s_diff


def rank_videos(
    videos: list[dict[str, Any]],
    *,
    user_tags: set[str],
    user_pref_duration_sec: int,
    user_intensity: int,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """对候选视频按 ``score_video`` 降序取 Top-N。

    Returns:
        ``[{**video, "score": float}, ...]``

    """
    scored = [
        {
            **v,
            "score": score_video(
                v,
                user_tags=user_tags,
                user_pref_duration_sec=user_pref_duration_sec,
                user_intensity=user_intensity,
            ),
        }
        for v in videos
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


# ─────────────────────────────────────────────────────────────────────────────
# §三 引擎入口（声明式 YAML → 调用 score_video）
# ─────────────────────────────────────────────────────────────────────────────
def run(name: str, *, context: dict[str, Any]) -> Any:
    """Execute a named rule set with the given context.

    Args:
        name: 规则集名（如 ``video_match``）。
        context: 含 videos / user_tags / duration / intensity / top_n 等键的字典。

    Returns:
        ``list[dict]`` of ranked videos.

    """
    _ = load_rule(name)  # validate YAML exists & schema OK
    user_tags = set(context.get("user_tags") or [])
    return rank_videos(
        videos=context.get("videos") or [],
        user_tags=user_tags,
        user_pref_duration_sec=int(context.get("duration") or 600),
        user_intensity=int(context.get("intensity") or 3),
        top_n=int(context.get("top_n") or 10),
    )


__all__ = ["rank_videos", "run", "score_video"]
