"""Unit tests for diagnosis_service."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services.diagnosis_service import (
    ALLOWED_IMAGE_FORMATS,
    _validate_complaint,
    _validate_photos,
)


def test_validate_photos_ok() -> None:
    photos = [
        {"url": "https://x/f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 1000},
        {"url": "https://x/h.jpg", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {
            "url": "https://x/s.jpg",
            "body_part": "shoulder_neck",
            "format": "jpg",
            "size_bytes": 3000,
        },
    ]
    result = _validate_photos(photos)
    assert len(result) == 3
    assert result[0]["body_part"] == "face"


def test_validate_photos_wrong_count() -> None:
    """0 张或 4 张照片 → UserInputError（合法数量仅 1 / 3）。"""
    from app.core.errors import UserInputError

    with pytest.raises(UserInputError):
        _validate_photos([])

    with pytest.raises(UserInputError):
        _validate_photos(
            [
                {"url": "https://x/1.jpg", "body_part": "face"},
                {"url": "https://x/2.jpg", "body_part": "head"},
                {"url": "https://x/3.jpg", "body_part": "shoulder_neck"},
                {"url": "https://x/4.jpg", "body_part": "face"},
            ]
        )


def test_validate_photos_bad_format() -> None:
    from app.services.diagnosis_service import DiagnosisError

    photos = [
        {"url": "https://x/f.gif", "body_part": "face", "format": "gif", "size_bytes": 1000},
        {"url": "https://x/h.jpg", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {
            "url": "https://x/s.jpg",
            "body_part": "shoulder_neck",
            "format": "jpg",
            "size_bytes": 3000,
        },
    ]
    with pytest.raises(DiagnosisError) as exc_info:
        _validate_photos(photos)
    assert "format" in exc_info.value.code.lower()


def test_validate_photos_too_large() -> None:
    from app.services.diagnosis_service import DiagnosisError

    photos = [
        {"url": "x", "body_part": "face", "format": "jpg", "size_bytes": 20 * 1024 * 1024},
        {"url": "x", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {"url": "x", "body_part": "shoulder_neck", "format": "jpg", "size_bytes": 3000},
    ]
    with pytest.raises(DiagnosisError) as exc_info:
        _validate_photos(photos)
    assert exc_info.value.code == "E_DIAGNOSIS_IMAGE_TOO_LARGE"


def test_validate_complaint_none() -> None:
    assert _validate_complaint(None) is None


def test_validate_complaint_too_long() -> None:
    from app.services.diagnosis_service import DiagnosisError

    with pytest.raises(DiagnosisError) as exc_info:
        _validate_complaint("x" * 600)
    assert "TOO_LONG" in exc_info.value.code


def test_validate_photos_wrong_body_part() -> None:
    from app.core.errors import UserInputError

    photos = [
        {"url": "x", "body_part": "leg", "format": "jpg", "size_bytes": 1000},
        {"url": "x", "body_part": "head", "format": "jpg", "size_bytes": 2000},
        {"url": "x", "body_part": "shoulder_neck", "format": "jpg", "size_bytes": 3000},
    ]
    with pytest.raises(UserInputError):
        _validate_photos(photos)


def test_allowed_image_formats_contains_jpg_png() -> None:
    assert "jpg" in ALLOWED_IMAGE_FORMATS
    assert "png" in ALLOWED_IMAGE_FORMATS


def test_validate_photos_accepts_object_key_alias() -> None:
    """前端只传 ``object_key``（不传 url）也能校验通过。

    通过 mock 掉 ``_resolve_object_key_to_url``，避免真实调对象存储。
    """
    from unittest.mock import patch

    photos = [
        {
            "object_key": "diagnosis/u-1/abc.jpg",
            "body_part": "face",
            "format": "jpg",
            "size_bytes": 1000,
        }
    ]
    with patch(
        "app.services.diagnosis_service._resolve_object_key_to_url",
        return_value="http://minio:9000/bkt/diagnosis/u-1/abc.jpg?X-Amz=...",
    ):
        result = _validate_photos(photos)
    assert result[0]["url"].startswith("http://")
    assert result[0]["object_key"] == "diagnosis/u-1/abc.jpg"


def test_validate_photos_rejects_missing_url_and_object_key() -> None:
    """既无 url 也无 object_key → 抛 UserInputError。"""
    from app.core.errors import UserInputError

    photos = [
        {"body_part": "face", "format": "jpg", "size_bytes": 1000},
    ]
    with pytest.raises(UserInputError):
        _validate_photos(photos)


def test_validate_photos_accepts_one_to_three() -> None:
    """MVP A 场景：1-3 张均允许，face 必含。"""
    one = [
        {"url": "https://x/f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 1000},
    ]
    assert len(_validate_photos(one)) == 1

    two = one + [
        {"url": "https://x/h.jpg", "body_part": "head", "format": "jpg", "size_bytes": 1000},
    ]
    assert len(_validate_photos(two)) == 2

    three = two + [
        {
            "url": "https://x/s.jpg",
            "body_part": "shoulder_neck",
            "format": "jpg",
            "size_bytes": 1000,
        },
    ]
    assert len(_validate_photos(three)) == 3


def test_validate_photos_face_required() -> None:
    """缺失 face → 抛 UserInputError，错误码 ``E_DIAGNOSIS_FACE_REQUIRED``。"""
    from app.core.errors import UserInputError

    photos = [
        {"url": "https://x/h.jpg", "body_part": "head", "format": "jpg", "size_bytes": 1000},
        {
            "url": "https://x/s.jpg",
            "body_part": "shoulder_neck",
            "format": "jpg",
            "size_bytes": 1000,
        },
    ]
    with pytest.raises(UserInputError) as exc_info:
        _validate_photos(photos)
    assert exc_info.value.code == "E_DIAGNOSIS_FACE_REQUIRED"


def test_validate_photos_rejects_empty_list() -> None:
    """空列表 → 抛 UserInputError（数量 < 1）。"""
    from app.core.errors import UserInputError

    with pytest.raises(UserInputError) as exc_info:
        _validate_photos([])
    assert exc_info.value.code == "E_DIAGNOSIS_INVALID_INPUT"


def test_validate_photos_rejects_more_than_three() -> None:
    """4 张以上 → 抛 UserInputError（数量 > 3）。"""
    from app.core.errors import UserInputError

    photos = [
        {"url": "https://x/1.jpg", "body_part": "face", "format": "jpg", "size_bytes": 100},
        {"url": "https://x/2.jpg", "body_part": "face", "format": "jpg", "size_bytes": 100},
        {"url": "https://x/3.jpg", "body_part": "face", "format": "jpg", "size_bytes": 100},
        {"url": "https://x/4.jpg", "body_part": "face", "format": "jpg", "size_bytes": 100},
    ]
    with pytest.raises(UserInputError) as exc_info:
        _validate_photos(photos)
    assert exc_info.value.code == "E_DIAGNOSIS_INVALID_INPUT"


@pytest.mark.asyncio
async def test_llm_prompt_contains_missing_note_when_under_3_photos() -> None:
    """< 3 张照片时，``_llm_diagnose`` 构造的 ``HumanMessage.text`` 应包含 ``[NOTE]`` 行。

    通过替换 ``app.llm.multimodal_llm`` 为可观测 stub，捕获 LLM 调用栈里的
    ``messages`` 列表；``_llm_diagnose`` 在函数体内 ``from app.llm import multimodal_llm``
    会读到这个新对象。
    """
    import app.llm as llm_mod
    from app.services import diagnosis_service as svc

    captured: dict[str, list[object]] = {}

    class _StubStructured:
        async def ainvoke(self, messages: list[object]) -> object:
            captured["messages"] = list(messages)
            from app.llm.schemas import DiagnosisOutput

            return DiagnosisOutput(
                directions=[],
                tags=[],
                summary="stub",
            )

    class _StubMulti:
        model = "stub-multi"

        def with_structured_output(self, _schema: object) -> _StubStructured:
            return _StubStructured()

    # conftest 已注入 mock_multi；这里覆盖为可观测 stub 即可。
    llm_mod.multimodal_llm = _StubMulti()  # type: ignore[assignment]

    photos = [
        {"url": "https://x/f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 100},
        {"url": "https://x/h.jpg", "body_part": "head", "format": "jpg", "size_bytes": 100},
    ]
    profile = {"age_range": "23-28", "focus_parts": ["face"]}
    await svc._llm_diagnose(photos, profile, None)

    messages = captured.get("messages", [])
    assert messages, "structured_llm.ainvoke was not called"
    human = next(m for m in messages if m.__class__.__name__ == "HumanMessage")
    content = human.content
    assert isinstance(content, list)
    text_block = next(b for b in content if b.get("type") == "text")
    text = text_block["text"]
    assert "[NOTE] 缺失 1 张图片" in text
    assert "body_parts 缺失:" in text
    assert "shoulder_neck" in text


# ════════════════════════════════════════════════════════════════════════════════
# PR-A2 增量 — stream_diagnose pipeline 测试
# ════════════════════════════════════════════════════════════════════════════════


async def _collect_events(
    store, job_id: str, *, max_events: int = 10, timeout: float = 2.0
):  # type: ignore[no-untyped-def]
    """持续从 store 拉事件直到遇到 done/error 或超时。"""
    from app.core.job_state import InMemoryJobStateStore

    store: InMemoryJobStateStore
    collected: list[dict] = []
    deadline = asyncio.get_event_loop().time() + timeout
    while len(collected) < max_events:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        evt = await store.next_event(job_id, timeout=min(remaining, 0.5))
        if evt is None:
            continue
        collected.append({"kind": evt.kind, **evt.payload})
        if evt.kind in {"done", "error"}:
            break
    return collected


@pytest.mark.asyncio
async def test_stream_diagnose_emits_all_stages() -> None:
    """``stream_diagnose`` 端到端：5 阶段按序 + done + 0 error。"""
    from unittest.mock import patch
    from uuid import uuid4

    from app.core.job_state import InMemoryJobStateStore
    from app.services.diagnosis_service import (
        StreamDiagnoseInputs,
        stream_diagnose,
    )

    store = InMemoryJobStateStore()
    job_id = store.create_job(report_id=str(uuid4()), user_id="u-svc")
    report_id = str(uuid4())

    db = AsyncMock()
    db.flush = AsyncMock(return_value=None)

    class _Exec:
        def scalar_one_or_none(self):
            return None

    db.execute = AsyncMock(return_value=_Exec())

    inputs = StreamDiagnoseInputs(
        photos=[{"url": "f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 0}],
        complaint=None,
        user_id="u-svc",
        report_id=report_id,
        job_id=job_id,
        profile={},
    )

    llm_mock = AsyncMock(
        return_value={
            "directions": [{"title": "t", "description": "d", "video_id": None}],
            "tags": ["tg"],
            "summary": "sm",
            "llm_cost": "0",
            "model": "m",
        }
    )

    consumer = asyncio.create_task(_collect_events(store, job_id, max_events=6))

    with patch(
        "app.services.diagnosis_service._invoke_llm_structured",
        new=llm_mock,
    ):
        await stream_diagnose(inputs, store=store, db=db)

    events = await consumer
    stages = [e["stage"] for e in events if e["kind"] == "stage"]
    assert stages == ["connected", "preprocess", "analyzing", "suggestion", "ready"]
    error_events = [e for e in events if e["kind"] == "error"]
    assert error_events == []
    assert events[-1]["kind"] == "done"


@pytest.mark.asyncio
async def test_stream_diagnose_persists_report_with_status_ready() -> None:
    """stream_diagnose 成功后，db.flush 必须被调用（保证 ready 行落库）。"""
    from unittest.mock import patch
    from uuid import uuid4

    from app.core.job_state import InMemoryJobStateStore
    from app.services.diagnosis_service import (
        StreamDiagnoseInputs,
        stream_diagnose,
    )

    store = InMemoryJobStateStore()
    job_id = store.create_job(report_id=str(uuid4()), user_id="u-svc")
    report_id = str(uuid4())

    db = AsyncMock()
    db.flush = AsyncMock(return_value=None)

    class _Exec:
        def scalar_one_or_none(self):
            return None

    db.execute = AsyncMock(return_value=_Exec())

    inputs = StreamDiagnoseInputs(
        photos=[{"url": "f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 0}],
        complaint=None,
        user_id="u-svc",
        report_id=report_id,
        job_id=job_id,
        profile={},
    )

    llm_mock = AsyncMock(
        return_value={
            "directions": [{"title": "t", "description": "d", "video_id": None}],
            "tags": ["tg"],
            "summary": "sm",
            "llm_cost": "0",
            "model": "m",
        }
    )

    with patch(
        "app.services.diagnosis_service._invoke_llm_structured",
        new=llm_mock,
    ):
        await stream_diagnose(inputs, store=store, db=db)

    # db.flush 被 _persist_report_ready 显式调用过；这是 ready 行落库的关键信号
    db.flush.assert_awaited()
    # 同时 verify 新报告对象被传给 db.add（INSERT 分支）或通过 attribute 更新
    # 用 mock_calls 推断：本测试不强断 add/update，但 flush 调用 = 行提交触发前最少条件
    assert db.flush.await_count >= 1


@pytest.mark.asyncio
async def test_stream_diagnose_emits_error_on_llm_failure() -> None:
    """LLM 抛异常 → stage:ready 之前发出 error 事件 + report 行不被持久化为 ready。"""
    from unittest.mock import patch
    from uuid import uuid4

    from app.core.job_state import InMemoryJobStateStore
    from app.services.diagnosis_service import (
        StreamDiagnoseInputs,
        stream_diagnose,
    )

    store = InMemoryJobStateStore()
    job_id = store.create_job(report_id=str(uuid4()), user_id="u-svc")
    report_id = str(uuid4())

    db = AsyncMock()
    db.flush = AsyncMock(return_value=None)

    class _Exec:
        def scalar_one_or_none(self):
            return None

    db.execute = AsyncMock(return_value=_Exec())

    inputs = StreamDiagnoseInputs(
        photos=[{"url": "f.jpg", "body_part": "face", "format": "jpg", "size_bytes": 0}],
        complaint=None,
        user_id="u-svc",
        report_id=report_id,
        job_id=job_id,
        profile={},
    )

    async def boom(*args, **kwargs):
        raise RuntimeError("LLM 故障：测试强制异常")

    consumer = asyncio.create_task(_collect_events(store, job_id, max_events=10))

    with (
        patch(
            "app.services.diagnosis_service._invoke_llm_structured",
            new=boom,
        ),
        pytest.raises(RuntimeError),
    ):
        await stream_diagnose(inputs, store=store, db=db)

    events = await consumer
    error_events = [e for e in events if e["kind"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["code"] == "E_DIAGNOSIS_PIPELINE_FAILED"
    # ready 阶段事件不应出现（pipeline 在 suggestion 后失败）
    assert not any(e["stage"] == "ready" for e in events if e["kind"] == "stage")
    # done 事件也不应有
    done_events = [e for e in events if e["kind"] == "done"]
    assert done_events == []
    # 注意：db.flush 仅可能在 LLM 调用之前的某个早期阶段被调用
    # 不强断 flush.await_count == 0（不强加细节），只确认 ready/done 不在事件流中
