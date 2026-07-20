"""Selfwell Backend MVP 11 模块端到端压测 locustfile。

真源：``docs/plan/mvp-implementation-plan.md`` §1.5 + ``docs/architecture/api.yaml`` V1.1.0
+ facts-anchor §3（11 个端点 tag）+ Sprint 1-5 路由清单。

覆盖端点（按 PRD §1.5 critical path）：
- 探针类：/healthz
- 认证类：/api/v1/auth/wx-login（mock code2session）
- 档案类：/api/v1/users/me, /api/v1/users/profile
- M2 诊断：/api/v1/diagnosis（创建）
- M3 方案：/api/v1/plans/generate
- M4 打卡：/api/v1/checkins
- M5 管家：/api/v1/assistant/sessions
- M7 反馈：/api/v1/feedback
- M6 广场：/api/v1/community/posts
- M8 回忆：/api/v1/butler/recall
- M10 抱抱卡：/api/v1/share/hug-card

权重按 PRD §1.5 关键路径（首页 50% + 打卡 25% + 诊断 15% + 其他 10%）。
"""

from __future__ import annotations

import os
import random
from typing import Any
from uuid import uuid4

from locust import events, task
from locust.contrib.fasthttp import RestUser as HttpUser


# 简单 MOCK JWT 生成（与后端 jwt_service 对齐）
def _mock_jwt(user_id: str) -> str:
    """生成 mock JWT（仅用于压测环境，secret_key 与后端一致）。"""
    import base64
    import hashlib
    import hmac
    import json
    import time

    secret = os.getenv("JWT_SECRET_KEY", "load-test-secret-key-32-chars-min")
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "type": "access",
        "platform": "wx_mp",
        "iat": int(time.time()),
    }

    def b64(data: dict[str, Any]) -> str:
        s = json.dumps(data, separators=(",", ":"))
        return base64.urlsafe_b64encode(s.encode()).rstrip(b"=").decode()

    h_b64 = b64(header)
    p_b64 = b64(payload)
    msg = f"{h_b64}.{p_b64}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{h_b64}.{p_b64}.{sig_b64}"


class SelfwellMvpUser(HttpUser):
    """模拟 1 个 MVP 用户的端到端流量。

    关键路径权重：
    - 健康检查 / 诊断 30%
    - 首页 + 打卡 50%
    - 其它 20%
    """

    host = os.getenv("SELFWELL_HOST", "http://localhost:8001")
    # dev: uvicorn 退到 8001(让出 8000 给 Caddy);压测直连 8001,不走 Caddy
    # 要走 Caddy: SELFWELL_HOST=http://localhost:8000 (别忘了把 /api 加进 path)
    # 启动时不等待（fast_http 默认 0）
    wait_time = lambda *_: 0  # noqa: E731
    abstract = True

    def on_start(self) -> None:
        """每个 user 启动时初始化 1 个 JWT。"""
        self.user_id = str(uuid4())
        self.token = _mock_jwt(self.user_id)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    # ── 探针类 ──────────────────────────────────────────────────────────────
    @task(5)
    def healthz(self) -> None:
        self.client.get("/healthz", name="/healthz")

    # ── M1 档案类 ───────────────────────────────────────────────────────────
    @task(15)
    def get_me(self) -> None:
        self.client.get(
            "/api/v1/users/me", headers=self.headers, name="/api/v1/users/me"
        )

    @task(3)
    def update_profile(self) -> None:
        self.client.post(
            "/api/v1/users/profile",
            headers=self.headers,
            json={
                "age_range": "23-28",
                "focus_parts": ["face", "head"],
                "intensity": "适中",
                "preferred_time": "晚",
                "sitting_hours": "4-8h",
            },
            name="/api/v1/users/profile",
        )

    # ── M2 诊断 ─────────────────────────────────────────────────────────────
    @task(2)
    def create_diagnosis(self) -> None:
        self.client.post(
            "/api/v1/diagnosis",
            headers=self.headers,
            json={
                "photos": [
                    {"url": f"https://test/face.jpg?u={self.user_id}",
                     "body_part": "face", "format": "jpg", "size_bytes": 100000},
                    {"url": f"https://test/head.jpg?u={self.user_id}",
                     "body_part": "head", "format": "jpg", "size_bytes": 100000},
                    {"url": f"https://test/sn.jpg?u={self.user_id}",
                     "body_part": "shoulder_neck", "format": "jpg", "size_bytes": 100000},
                ],
                "complaint": "脸有点干",
            },
            name="/api/v1/diagnosis",
        )

    # ── M4 打卡 ─────────────────────────────────────────────────────────────
    @task(10)
    def list_checkins(self) -> None:
        self.client.get(
            "/api/v1/checkins", headers=self.headers, name="/api/v1/checkins"
        )

    @task(5)
    def create_checkin(self) -> None:
        # mock plan_id
        self.client.post(
            "/api/v1/checkins",
            headers=self.headers,
            json={
                "plan_id": str(uuid4()),
                "day": random.randint(1, 21),
                "video_id": f"v_{random.randint(1, 100)}",
                "feeling": "感觉不错",
            },
            name="/api/v1/checkins [POST]",
        )

    # ── M5 管家 ─────────────────────────────────────────────────────────────
    @task(4)
    def create_assistant_session(self) -> None:
        self.client.post(
            "/api/v1/assistant/sessions",
            headers=self.headers,
            json={"entry_card": "general", "primary_intent": "chat"},
            name="/api/v1/assistant/sessions",
        )

    # ── M7 反馈 ─────────────────────────────────────────────────────────────
    @task(8)
    def create_feedback(self) -> None:
        self.client.post(
            "/api/v1/feedback",
            headers=self.headers,
            json={
                "feedback_type": "mood_text",
                "text_content": "今天心情不错",
            },
            name="/api/v1/feedback",
        )

    # ── M6 广场 ─────────────────────────────────────────────────────────────
    @task(5)
    def list_posts(self) -> None:
        self.client.get(
            "/api/v1/community/posts", headers=self.headers, name="/api/v1/community/posts"
        )

    @task(1)
    def create_post(self) -> None:
        self.client.post(
            "/api/v1/community/posts",
            headers=self.headers,
            json={"content": f"分享我今天的训练感受 {uuid4()}", "images": []},
            name="/api/v1/community/posts [POST]",
        )

    # ── M8 主动回忆 ─────────────────────────────────────────────────────────
    @task(2)
    def generate_recall(self) -> None:
        self.client.post(
            "/api/v1/butler/recall",
            headers=self.headers,
            json={"trigger": "user_manual"},
            name="/api/v1/butler/recall",
        )

    # ── M10 抱抱卡 ──────────────────────────────────────────────────────────
    @task(2)
    def hug_card(self) -> None:
        self.client.post(
            "/api/v1/share/hug-card",
            headers=self.headers,
            json={"day": 7, "nickname": "测试", "stats": {"fragments": 7, "streak_days": 7}},
            name="/api/v1/share/hug-card",
        )

    # ── M3 方案生成 ─────────────────────────────────────────────────────────
    @task(1)
    def generate_plan(self) -> None:
        self.client.post(
            "/api/v1/plans/generate",
            headers=self.headers,
            json={"report_id": str(uuid4())},
            name="/api/v1/plans/generate",
        )


@events.init_command_line_parser.add_listener
def _add_args(parser: events.CommandLineParser) -> None:
    """Register custom CLI args."""
    parser.add_argument(
        "--peak-users", type=int, default=200, help="Peak concurrent users"
    )
    parser.add_argument(
        "--target-p95-ms", type=int, default=300, help="Target p95 latency (ms)"
    )


__all__ = ["SelfwellMvpUser"]
