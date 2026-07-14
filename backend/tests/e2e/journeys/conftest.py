"""E2E 旅程测试共享 fixtures（Phase 4 · 批次 5）。

设计原则：
1. 用 ASGITransport 直接驱动已加载的 FastAPI app（无需真实 uvicorn 端口，避免
   Windows 下 `--reload` 致命错误）。
2. 用 sign_access_token 模拟登录用户，避免对外部微信 / 手机号通道的依赖。
3. 复用批次 1 数据治理铺设的 USER_1 / USER_2，避免在测试里硬重建用户。

环境前置：
- Postgres / Redis / MinIO 运行中（docker compose）
- `tools/seed/run_all.py` 已执行（plans/checkins/feedback/recall_sessions/videos 已就位）
- JWT_SECRET_KEY 已配置且 ≥ 32 字符（``app_config.is_jwt_configured``）
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# 测试环境的 JWT secret：与 conftest_app.py/seed 脚本一致（>= 32 字符）
os.environ.setdefault("JWT_SECRET_KEY", "change_me_in_dev_only_at_least_32_chars_long_xxxxxxxxxxxxx")
os.environ["SELFWELL_USE_MOCK_LLM"] = "0"


# ─────────────────────────────────────────────────────────────────────────
# §0 Live backend base URL — 优先 HTTP 模式，绕开 in-process engine loop 复用问题
# ─────────────────────────────────────────────────────────────────────────
LIVE_BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8001")


# ─────────────────────────────────────────────────────────────────────────
# §1 用户常量：与 tools/seed/seed_plans.py / seed_checkins.py 对齐
# ─────────────────────────────────────────────────────────────────────────
USER_1 = UUID("40e10a9e-329f-4998-a3f0-d36c0ab08abf")
USER_2 = UUID("f255dff8-9f47-43a6-91c4-932b00c0447f")
USER_IDS = [USER_1, USER_2]

# 与 tools/seed/seed_plans.py:REPORT_IDS 对齐
REPORT_IDS = [
    "f7795686-7417-4ae8-ba16-62e15b98d68a",
    "a021d6bc-c3af-46e0-940b-62c237006a83",
    "6c7401f7-1d01-4d80-b1f7-674ecbb829c2",
    "3b1b630c-bb61-4bdc-8790-1bcab2297a52",
    "c9b0fa79-ed2c-4ea2-a3eb-74edc92f570c",
    "91f2c7aa-348e-45ec-bc67-accc020aa038",
    "fa510d9e-a295-4a0a-801b-23ddb9e7427c",
    "9cc8a1ce-3c33-4bbd-9f8b-0be5fb846145",
    "52fcbbd5-168c-452e-9e07-667ebd5a7d24",
    "5ee60413-9914-4aff-bca4-9a91283f342b",
]


# ─────────────────────────────────────────────────────────────────────────
# §2 fastapi app + JWT helper
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture
def fastapi_app():
    """导入 FastAPI app 实例。

    用 function 作用域而非 session —— 配合 pytest-asyncio strict 模式，
    避免 SQLAlchemy async engine 跨 event loop 复用导致 ``Event loop is closed``
    / ``NoneType.send``（asyncpg 在 loop 关闭后复用 transport 会崩）。
    """
    from app.main import app

    return app


@pytest.fixture
def jwt_for_user():
    """返回签 JWT 的工厂函数。

    Usage:
        token = jwt_for_user(str(USER_1))
        headers = {"Authorization": f"Bearer {token}"}
    """
    from app.auth.jwt_handler import sign_access_token

    def _make(user_id: str) -> str:
        return sign_access_token(user_id=user_id)

    return _make


@pytest.fixture
def auth_header_factory(jwt_for_user):
    """返回构造 Authorization 头的工厂函数。"""
    def _make(user_id: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {jwt_for_user(user_id)}"}

    return _make


# ─────────────────────────────────────────────────────────────────────────
# §3 AsyncClient（ASGI transport）
# ─────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def reset_sqlalchemy_engine() -> AsyncIterator[None]:
    """Dispose the runtime engine on the current pytest event loop.

    Application modules import ``app.db.session``. Importing
    ``backend.app.db.session`` here creates a second module object and leaves the
    engine used by requests untouched, so asyncpg connections leak into the next
    function-scoped loop.
    """
    from app.db.session import dispose_engine, set_engine_for_test

    try:
        await dispose_engine()
    except (AttributeError, RuntimeError):
        set_engine_for_test(None)

    yield

    try:
        await dispose_engine()
    except (AttributeError, RuntimeError):
        set_engine_for_test(None)


@pytest_asyncio.fixture
async def async_client(fastapi_app, reset_sqlalchemy_engine):
    """异步 HTTP 客户端。

    优先用真实 uvicorn（``E2E_BASE_URL`` 或默认 ``http://127.0.0.1:8001``），
    完全绕开 pytest-asyncio 在 function scope 下复用 SQLAlchemy engine 的 loop 复用问题。
    ASGITransport 模式保留作本地兜底（``E2E_BASE_URL=inproc`` 时启用）。
    """
    base_url = LIVE_BASE_URL
    if base_url == "inproc":
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://testserver", timeout=30.0) as client:
            yield client
        return
    async with AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


# ─────────────────────────────────────────────────────────────────────────
# §3b Cross-test shared context（session scope dict）
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def shared_ctx() -> dict[str, object]:
    """跨 test 共享的小型上下文（session scope）。

    用 pytest.session.* 这种用法在 pytest 9.x 已经移除（AttributeError）。
    测试里通过 fixture 参数显式注入，替代 ``pytest.session.xxx = ...``。
    """
    return {}


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    """E2E base URL。可通过 E2E_BASE_URL 改为指向真实 uvicorn 端口。

    默认留空，所有旅程走 ASGITransport；若设置了 E2E_BASE_URL 则用真实端口。
    """
    return os.environ.get("E2E_BASE_URL", "")


@pytest.fixture(scope="session", autouse=True)
def _env_preflight() -> Iterator[None]:
    """E2E 前置守卫：依赖段已配置。

    用 session 作用域是因为这是个**纯同步**的导入 + 配置 check，不跨 event loop。
    """
    from app.conf.app_config import app_config

    assert app_config.is_jwt_configured, (
        f"JWT secret_key len={len(app_config.jwt.secret_key)} 必须 ≥ 32 字符，"
        "配置未就绪会导致所有路由 500。检查 .env 的 JWT_SECRET_KEY。"
    )
    assert app_config.is_postgres_configured, "POSTGRES_PASSWORD 未配置"
    yield


# ─────────────────────────────────────────────────────────────────────────
# §6 LLM 真实实例覆写（优先于 backend/tests/conftest.py 的 mock_llm autouse）

@pytest.fixture(scope="session", autouse=True)
def _real_llm() -> Iterator[None]:
    """在 backend/tests/conftest.py 的 autouse mock_llm 之后执行，强制恢复真实 LLM。

    fixture 加载顺序（pytest 内部顺序）：
    1. backend/conftest.py（scope=session，autouse=True）—— 已执行
    2. backend/tests/conftest.py（scope=function，autouse=True）—— mock 已注入
    3. backend/tests/e2e/journeys/conftest.py（scope=session，autouse=True）—— 后追加载，覆盖 mock

    通过 re-import 链重绑定 app.llm 模块级变量，让后续 service 层导入拿到真实实例。
    """
    import app.llm as llm_module

    # 真实实例（已在模块顶部初始化）
    _real_text_llm = llm_module._text_llm
    _real_multimodal_llm = llm_module._multimodal_llm

    # 覆盖兼容别名
    llm_module.llm = _real_text_llm
    llm_module.text_llm = _real_text_llm
    llm_module.multimodal_llm = _real_multimodal_llm

    yield

    # restore mock
    llm_module.llm = llm_module._text_llm
    llm_module.text_llm = llm_module._text_llm
    llm_module.multimodal_llm = llm_module._multimodal_llm


# ─────────────────────────────────────────────────────────────────────────
# §7 SSE 帧解析 helpers
# ─────────────────────────────────────────────────────────────────────────
def parse_sse_chunk(chunk: str) -> list[tuple[str | None, Any]]:
    """解析一段 SSE 输出（多帧），返回 ``[(event, data), ...]`` 列表。"""
    import json

    out: list[tuple[str | None, Any]] = []
    pieces = chunk.split("\n\n")
    for piece in pieces:
        if not piece.strip():
            continue
        event: str | None = None
        data_lines: list[str] = []
        for raw_line in piece.split("\n"):
            line = raw_line.replace("\r", "")
            if not line or line.startswith(":"):
                continue
            if ":" not in line:
                continue
            field, _, value = line.partition(":")
            if value.startswith(" "):
                value = value[1:]
            if field == "event":
                event = value
            elif field == "data":
                data_lines.append(value)
        if event and data_lines:
            try:
                parsed: Any = json.loads("\n".join(data_lines))
            except json.JSONDecodeError:
                parsed = "\n".join(data_lines)
            out.append((event, parsed))
    return out


def _check_any_5xx(response) -> None:
    """任何 5xx 立刻报错（按任务要求）。"""
    if 500 <= response.status_code < 600:
        raise AssertionError(
            f"5xx detected (status={response.status_code}): "
            f"{response.text[:300] if hasattr(response, 'text') else ''}"
        )
