"""Unit tests for video_match scoring algorithm."""

from __future__ import annotations

from app.services.video_match import jaccard_similarity, rank_videos, score_video


def test_jaccard_similarity_basic() -> None:
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == 1 / 3
    assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard_similarity({"a"}, {"b"}) == 0.0


def test_jaccard_empty() -> None:
    assert jaccard_similarity(set(), {"a"}) == 0.0
    assert jaccard_similarity({"a"}, set()) == 0.0


def test_score_video_perfect_match() -> None:
    video = {"tags": ["face", "head"], "duration_sec": 900, "difficulty": 3}
    score = score_video(video, {"face", "head"}, intensity="适中", preferred_time="中")
    assert 0.9 < score <= 1.0  # 0.5*1 + 0.3*1 + 0.2*1 = 1.0


def test_score_video_no_tag_match() -> None:
    video = {"tags": ["leg"], "duration_sec": 900, "difficulty": 3}
    score = score_video(video, {"face", "head"}, intensity="适中", preferred_time="中")
    # tag=0, duration=1, difficulty=1 → 0 + 0.3 + 0.2 = 0.5
    assert 0.45 < score < 0.55


def test_score_video_weight_5_3_2() -> None:
    """验证 0.5/0.3/0.2 权重比例。"""
    v_match = {"tags": ["face"], "duration_sec": 900, "difficulty": 3}
    v_time = {"tags": ["face"], "duration_sec": 0, "difficulty": 3}
    v_diff = {"tags": ["face"], "duration_sec": 900, "difficulty": 5}
    s_match = score_video(v_match, ["face"], intensity="适中", preferred_time="中")
    s_time = score_video(v_time, ["face"], intensity="适中", preferred_time="中")
    s_diff = score_video(v_diff, ["face"], intensity="适中", preferred_time="中")
    # tag 贡献 0.5 最高
    assert s_match > s_time
    assert s_match > s_diff


def test_rank_videos() -> None:
    videos = [
        {"id": "v1", "tags": ["face"], "duration_sec": 900, "difficulty": 3},
        {"id": "v2", "tags": ["leg"], "duration_sec": 900, "difficulty": 3},
    ]
    ranked = rank_videos(videos, ["face"], intensity="适中", preferred_time="中")
    assert ranked[0]["id"] == "v1"
    assert "score" in ranked[0]


def test_rank_videos_top_k() -> None:
    videos = [
        {"id": f"v{i}", "tags": ["face"], "duration_sec": 900, "difficulty": 3} for i in range(5)
    ]
    ranked = rank_videos(videos, ["face"], top_k=2)
    assert len(ranked) == 2
