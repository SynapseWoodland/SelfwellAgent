"""M5 智能管家 SSE 链路集成测试。

测试场景：
- 场景 A: 无图聊天（chat 模式）
- 场景 B: 有图智能分析（smart_analyze mock 模式）
- 场景 C: Session 不存在错误处理

用法：
    python backend/scripts/test_assistant_sse.py
    python backend/scripts/test_assistant_sse.py --base-url http://localhost:8001
    python backend/scripts/test_assistant_sse.py --help
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import httpx

# Correct path: backend/ is the parent of scripts/, so 'app' is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.auth.jwt_handler import sign_access_token


# ─── CLI Args ─────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M5 智能管家 SSE 链路集成测试")
    parser.add_argument(
        "--base-url",
        # 1.1 起 uvicorn 退到 8001（让 8000 给 Caddy）；通过 Caddy 走 8000 也可以：
        #   --base-url http://127.0.0.1:8000/api/v1
        default="http://127.0.0.1:8001",
        help="API base URL (default: http://127.0.0.1:8001)",
    )
    parser.add_argument(
        "--user-id",
        default="f255dff8-9f47-43a6-91c4-932b00c0447f",
        help="Test user ID (UUID format)",
    )
    return parser.parse_args()


# ─── SSE Parser ────────────────────────────────────────────────────────────────

SSE_EVENT_RE = re.compile(r"event: ([^\n]+)\ndata: ([^\n]+(?:\n(?![a-z]+:)[^\n]+)*)")
SSE_DATA_RE = re.compile(r"data: (.+)")


@dataclass
class SSEEvent:
    """Parsed SSE event."""
    type: str
    data: dict


def parse_sse_chunk(chunk: bytes) -> list[SSEEvent]:
    """Parse SSE data from a chunk of bytes.

    Handles:
    - Single event: b'event: token_delta\\ndata: {"token":"你"}\n\n'
    - Multiple events concatenated
    - Trailing newlines
    """
    text = chunk.decode("utf-8", errors="replace")
    events: list[SSEEvent] = []

    # Split by double newline (SSE message boundary)
    raw_messages = re.split(r"\n\n+", text)
    for raw in raw_messages:
        if not raw.strip():
            continue

        # Extract event type
        event_type = "message"  # default
        data_text = raw

        lines = raw.split("\n")
        data_lines = []
        for line in lines:
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())

        if data_lines:
            data_text = "\n".join(data_lines)
            try:
                data = json.loads(data_text)
            except json.JSONDecodeError:
                data = {"raw": data_text}

            events.append(SSEEvent(type=event_type, data=data))

    return events


# ─── Test Result Tracking ──────────────────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    passed: bool
    expected: str
    actual: str
    details: str = ""


results: list[TestResult] = []


def record(
    name: str,
    passed: bool,
    expected: str,
    actual: str,
    details: str = "",
) -> None:
    status = "PASS" if passed else "FAIL"
    results.append(TestResult(name, passed, expected, actual, details))
    print(f"[{status}] {name}")
    print(f"       Expected: {expected}")
    print(f"       Actual:   {actual}")
    if details:
        print(f"       Details:  {details[:200]}")
    print()


# ─── SSE Client Helpers ─────────────────────────────────────────────────────────

def sse_post(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    """Send a POST request expecting SSE streaming response."""
    with client.stream("POST", url, **kwargs) as response:
        # Read entire stream
        content = b""
        for chunk in response.iter_bytes():
            content += chunk
        # Return non-streaming response with content
        r = httpx.Response(
            status_code=response.status_code,
            content=content,
            headers=dict(response.headers),
            request=response.request,
        )
        return r


async def sse_post_async(client: httpx.AsyncClient, url: str, **kwargs) -> tuple[int, list[SSEEvent]]:
    """Send async POST request and parse SSE events.

    Returns:
        (status_code, list of parsed SSE events)
    """
    async with client.stream("POST", url, **kwargs) as response:
        content = b""
        async for chunk in response.aiter_bytes():
            content += chunk

        events = parse_sse_chunk(content)
        return response.status_code, events


# ─── Test Scenarios ────────────────────────────────────────────────────────────

def test_scenario_a_chat_mode(base_url: str, token: str, user_id: str) -> bool:
    """场景 A: 无图聊天（chat 模式）。

    预期 SSE 事件序列:
    - start
    - token_delta (多个)
    - end { "ok": true, "reply": "...", "persona_state": "..." }
    """
    print("\n" + "=" * 70)
    print("场景 A: 无图聊天（chat 模式）")
    print("=" * 70)

    client = httpx.Client(timeout=30.0)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    all_pass = True

    # Step 1: Create session
    print("[Step 1] 创建 Session...")
    create_resp = client.post(
        f"{base_url}/api/v1/assistant/sessions",
        headers=headers,
        json={"entry_card": "mood_diary", "primary_intent": "unknown"},
    )

    if create_resp.status_code not in (200, 201):
        record(
            "A-1 Create Session",
            False,
            "200 or 201",
            str(create_resp.status_code),
            create_resp.text[:200],
        )
        client.close()
        return False

    session_data = create_resp.json()
    session_id = session_data.get("data", {}).get("session_id")
    record(
        "A-1 Create Session",
        True,
        "200/201 with session_id",
        f"{create_resp.status_code}, session_id={session_id[:8]}...",
    )

    if not session_id:
        record("A-1b Get Session ID", False, "session_id exists", "None")
        client.close()
        return False
    record("A-1b Get Session ID", True, "session_id exists", str(session_id[:8]) + "...")

    # Step 2: Send chat message with SSE stream
    print("[Step 2] 发送聊天消息（你好）...")
    with client.stream(
        "POST",
        f"{base_url}/api/v1/assistant/sessions/{session_id}/messages",
        headers=headers,
        json={"text": "你好"},
    ) as resp:
        content = b""
        for chunk in resp.iter_bytes():
            content += chunk

    events = parse_sse_chunk(content)
    event_types = [e.type for e in events]
    print(f"       收到事件: {event_types}")

    # Verify event sequence
    # chat mode: start -> token_delta* -> end
    has_start = "start" in event_types
    has_token_delta = "token_delta" in event_types
    has_end = "end" in event_types

    record(
        "A-2a Has start event",
        has_start,
        "start in events",
        f"start={'start' in event_types}, types={event_types}",
    )
    all_pass &= has_start

    record(
        "A-2b Has token_delta events",
        has_token_delta,
        "token_delta in events",
        f"token_delta={has_token_delta}, count={event_types.count('token_delta')}",
    )
    all_pass &= has_token_delta

    record(
        "A-2c Has end event",
        has_end,
        "end in events",
        f"end={has_end}",
    )
    all_pass &= has_end

    # Verify end event content
    end_event = next((e for e in events if e.type == "end"), None)
    if end_event:
        ok = end_event.data.get("ok")
        reply = end_event.data.get("reply", "")
        persona_state = end_event.data.get("persona_state")

        record(
            "A-2d End event ok=true",
            ok is True,
            "ok == true",
            f"ok={ok}",
        )
        all_pass &= (ok is True)

        record(
            "A-2e End event has reply",
            bool(reply),
            "reply is non-empty",
            f"reply={reply[:50]}..." if len(reply) > 50 else f"reply={reply}",
        )
        all_pass &= bool(reply)

        record(
            "A-2f End event has persona_state",
            persona_state is not None,
            "persona_state exists",
            f"persona_state={persona_state}",
        )
        all_pass &= (persona_state is not None)
    else:
        record("A-2d-f End event content", False, "end event exists", "None")
        all_pass = False

    # Step 3: Verify messages stored
    print("[Step 3] 验证消息已存储...")
    msg_resp = client.get(
        f"{base_url}/api/v1/assistant/sessions/{session_id}/messages",
        headers=headers,
    )
    if msg_resp.status_code == 200:
        messages = msg_resp.json().get("data", [])
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        record(
            "A-3 Messages stored",
            len(user_msgs) > 0 and len(assistant_msgs) > 0,
            "user and assistant messages",
            f"user_msgs={len(user_msgs)}, assistant_msgs={len(assistant_msgs)}",
        )
        all_pass &= (len(user_msgs) > 0 and len(assistant_msgs) > 0)
    else:
        record("A-3 Messages stored", False, "200", str(msg_resp.status_code))
        all_pass = False

    client.close()
    return all_pass


def test_scenario_b_smart_analyze(base_url: str, token: str, user_id: str) -> bool:
    """场景 B: 有图智能分析（smart_analyze mock 模式）。

    预期 SSE 事件序列:
    - start
    - progress (step=1, percent=15, label="图片校验中")
    - progress (step=2, percent=45, label="正在分析体态")
    - progress (step=3, percent=75, label="生成养护建议")
    - progress (step=4, percent=100, label="分析完成")
    - report { "directions": [...], "tags": [...], "summary": "..." }
    - end { "ok": true, "reply": "...", "persona_state": "..." }
    """
    print("\n" + "=" * 70)
    print("场景 B: 有图智能分析（smart_analyze mock 模式）")
    print("=" * 70)

    client = httpx.Client(timeout=30.0)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    all_pass = True

    # Step 1: Create session
    print("[Step 1] 创建 Session...")
    create_resp = client.post(
        f"{base_url}/api/v1/assistant/sessions",
        headers=headers,
        json={"entry_card": "smart_analyze", "primary_intent": "unknown"},
    )

    if create_resp.status_code not in (200, 201):
        record(
            "B-1 Create Session",
            False,
            "200 or 201",
            str(create_resp.status_code),
            create_resp.text[:200],
        )
        client.close()
        return False

    session_data = create_resp.json()
    session_id = session_data.get("data", {}).get("session_id")
    record(
        "B-1 Create Session",
        True,
        "200/201 with session_id",
        f"{create_resp.status_code}, session_id={session_id[:8]}...",
    )

    if not session_id:
        record("B-1b Get Session ID", False, "session_id exists", "None")
        client.close()
        return False
    record("B-1b Get Session ID", True, "session_id exists", str(session_id[:8]) + "...")

    # Step 2: Send smart_analyze message with SSE stream
    print("[Step 2] 发送智能分析请求（带图片）...")
    with client.stream(
        "POST",
        f"{base_url}/api/v1/assistant/sessions/{session_id}/messages",
        headers=headers,
        json={
            "text": "智能分析",
            "image_keys": ["assistant/user123/test.jpg"],
            "body_parts": ["face"],
        },
    ) as resp:
        content = b""
        for chunk in resp.iter_bytes():
            content += chunk

    events = parse_sse_chunk(content)
    event_types = [e.type for e in events]
    print(f"       收到事件: {event_types}")

    # Verify event sequence
    has_start = "start" in event_types
    progress_count = event_types.count("progress")
    has_report = "report" in event_types
    has_end = "end" in event_types

    record(
        "B-2a Has start event",
        has_start,
        "start in events",
        f"start={has_start}",
    )
    all_pass &= has_start

    record(
        "B-2b Has 4 progress events",
        progress_count == 4,
        "4 progress events",
        f"progress_count={progress_count}",
    )
    all_pass &= (progress_count == 4)

    # Verify progress steps
    progress_events = [e for e in events if e.type == "progress"]
    expected_steps = [
        {"step": 1, "percent": 15, "label": "图片校验中"},
        {"step": 2, "percent": 45, "label": "正在分析体态"},
        {"step": 3, "percent": 75, "label": "生成养护建议"},
        {"step": 4, "percent": 100, "label": "分析完成"},
    ]

    for i, expected in enumerate(expected_steps):
        actual = progress_events[i].data if i < len(progress_events) else {}
        step_ok = actual.get("step") == expected["step"]
        percent_ok = actual.get("percent") == expected["percent"]
        label_ok = expected["label"] in actual.get("label", "")

        record(
            f"B-2c.{i+1} Progress step {expected['step']}",
            step_ok and percent_ok and label_ok,
            f"step={expected['step']}, percent={expected['percent']}, label={expected['label']}",
            f"step={actual.get('step')}, percent={actual.get('percent')}, label={actual.get('label')}",
        )
        all_pass &= (step_ok and percent_ok and label_ok)

    record(
        "B-2d Has report event",
        has_report,
        "report in events",
        f"report={has_report}",
    )
    all_pass &= has_report

    record(
        "B-2e Has end event",
        has_end,
        "end in events",
        f"end={has_end}",
    )
    all_pass &= has_end

    # Verify report event content
    report_event = next((e for e in events if e.type == "report"), None)
    if report_event:
        directions = report_event.data.get("directions", [])
        tags = report_event.data.get("tags", [])
        summary = report_event.data.get("summary")

        record(
            "B-2f Report has directions",
            len(directions) > 0,
            "directions is non-empty",
            f"directions_count={len(directions)}",
        )
        all_pass &= (len(directions) > 0)

        record(
            "B-2g Report has tags",
            isinstance(tags, list),
            "tags is list",
            f"tags_type={type(tags).__name__}",
        )
        all_pass &= isinstance(tags, list)

        record(
            "B-2h Report has summary",
            summary is not None,
            "summary exists",
            f"summary={str(summary)[:50]}..." if summary else "summary=None",
        )
        all_pass &= (summary is not None)
    else:
        record("B-2f-h Report content", False, "report event exists", "None")
        all_pass = False

    # Verify end event
    end_event = next((e for e in events if e.type == "end"), None)
    if end_event:
        ok = end_event.data.get("ok")
        record(
            "B-2i End event ok=true",
            ok is True,
            "ok == true",
            f"ok={ok}",
        )
        all_pass &= (ok is True)
    else:
        record("B-2i End event", False, "end event exists", "None")
        all_pass = False

    # Step 3: Verify messages stored
    print("[Step 3] 验证消息已存储...")
    msg_resp = client.get(
        f"{base_url}/api/v1/assistant/sessions/{session_id}/messages",
        headers=headers,
    )
    if msg_resp.status_code == 200:
        messages = msg_resp.json().get("data", [])
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        record(
            "B-3 Messages stored",
            len(user_msgs) > 0 and len(assistant_msgs) > 0,
            "user and assistant messages",
            f"user_msgs={len(user_msgs)}, assistant_msgs={len(assistant_msgs)}",
        )
        all_pass &= (len(user_msgs) > 0 and len(assistant_msgs) > 0)
    else:
        record("B-3 Messages stored", False, "200", str(msg_resp.status_code))
        all_pass = False

    client.close()
    return all_pass


def test_scenario_c_session_not_found(base_url: str, token: str) -> bool:
    """场景 C: Session 不存在错误处理。

    预期 HTTP 404 或 SSE error 事件。
    """
    print("\n" + "=" * 70)
    print("场景 C: Session 不存在错误处理")
    print("=" * 70)

    client = httpx.Client(timeout=30.0)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    all_pass = True
    fake_session_id = "00000000-0000-0000-0000-000000000000"

    # Step 1: Try to send message to non-existent session
    print(f"[Step 1] 发送消息到不存在的 Session: {fake_session_id}...")
    with client.stream(
        "POST",
        f"{base_url}/api/v1/assistant/sessions/{fake_session_id}/messages",
        headers=headers,
        json={"text": "测试"},
    ) as resp:
        content = b""
        for chunk in resp.iter_bytes():
            content += chunk

    # Check if we got HTTP 404 (preferred) or SSE error event
    is_404 = resp.status_code == 404
    is_410 = resp.status_code == 410
    is_http_error = is_404 or is_410

    # Parse SSE for error event
    events = parse_sse_chunk(content)
    has_error = any(e.type == "error" for e in events)
    has_end = any(e.type == "end" for e in events)
    end_ok = False
    for e in events:
        if e.type == "end":
            end_ok = e.data.get("ok") is False
            break

    # Either HTTP 404/410 OR SSE error event with ok=false is acceptable
    error_handled = is_http_error or (has_error and has_end and end_ok)

    record(
        "C-1 Session not found (HTTP 404/410)",
        is_http_error,
        "HTTP 404 or 410",
        f"HTTP {resp.status_code}",
    )
    all_pass &= is_http_error

    if not is_http_error:
        record(
            "C-1b Or SSE error event",
            has_error,
            "SSE error event",
            f"has_error={has_error}",
        )
        all_pass &= has_error

        if has_end:
            record(
                "C-1c End event ok=false",
                end_ok,
                "ok == false",
                f"ok={next((e.data.get('ok') for e in events if e.type == 'end'), None)}",
            )
            all_pass &= end_ok

    client.close()
    return all_pass


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    base_url = args.base_url
    user_id = args.user_id

    print("\n" + "=" * 70)
    print("M5 智能管家 SSE 链路集成测试")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"User ID:  {user_id}")
    print("=" * 70)

    # Generate auth token
    token = sign_access_token(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}

    # Check server connectivity
    print("\n[Pre-check] 检查服务器连接...")
    try:
        client = httpx.Client(timeout=5.0)
        resp = client.get(f"{base_url}/docs")
        client.close()
        if resp.status_code != 200:
            print(f"警告: 服务器返回 {resp.status_code}，测试可能无法正常执行")
        else:
            print("服务器连接正常")
    except Exception as e:
        print(f"错误: 无法连接到 {base_url}")
        print(f"       {e}")
        print("\n请确保后端服务正在运行:")
        print("   python -m uvicorn backend.app.main:app --reload")
        return 1

    # Run test scenarios
    all_pass = True

    all_pass &= test_scenario_a_chat_mode(base_url, token, user_id)
    all_pass &= test_scenario_b_smart_analyze(base_url, token, user_id)
    all_pass &= test_scenario_c_session_not_found(base_url, token)

    # Print summary
    print("\n" + "=" * 70)
    print("测试结果摘要")
    print("=" * 70)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed < total:
        print("\n失败用例:")
        for r in results:
            if not r.passed:
                print(f"  - {r.name}")
                print(f"    Expected: {r.expected}")
                print(f"    Actual:   {r.actual}")

    print("\n详细结果:")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name}")

    print("\n" + "=" * 70)
    if all_pass:
        print("所有测试通过!")
    else:
        print("部分测试失败!")
    print("=" * 70)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
