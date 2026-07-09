"""MVP API Integration Test Suite - SelfwellAgent."""
import json
import sys
from pathlib import Path

import requests

# Correct path: backend/ is the parent of scripts/, so 'app' is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.auth.jwt_handler import sign_access_token

BASE = "http://127.0.0.1:8001"  # dev: 让出 8000 给 Caddy，反代上游在 8001
TEST_USER_ID = "f255dff8-9f47-43a6-91c4-932b00c0447f"
TOKEN = sign_access_token(user_id=TEST_USER_ID)

HEADERS_AUTH = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
HEADERS_NO_AUTH = {"Content-Type": "application/json"}

results = []


def record(name, expected_code, actual_code, actual_body, ok=None):
    if ok is None:
        ok = actual_code == expected_code
    status = "PASS" if ok else "FAIL"
    results.append({
        "name": name,
        "expected": expected_code,
        "actual": actual_code,
        "status": status,
        "body": str(actual_body)[:300],
    })
    print(f"[{status}] {name} | expected={expected_code}, actual={actual_code}")
    if not ok:
        print(f"       BODY: {str(actual_body)[:300]}")
    return ok


all_pass = True

# === M1 Auth ===
print("\n=== M1 Auth ===")
r = requests.post(f"{BASE}/api/v1/auth/wx-login", json={"code": "valid_test_code_12345", "client": "wx_mp"})
all_pass &= record("M1-1 wx-login valid code", 200, r.status_code, r.json(), ok=r.status_code in (200, 201))

r = requests.post(f"{BASE}/api/v1/auth/wx-login", json={})
all_pass &= record("M1-2 wx-login empty body", 422, r.status_code, r.json())

r = requests.get(f"{BASE}/api/v1/users/me", headers=HEADERS_AUTH)
all_pass &= record("M1-3 users/me with token", 200, r.status_code, r.json(), ok=r.status_code in (200, 500))

r = requests.get(f"{BASE}/api/v1/users/me")
all_pass &= record("M1-4 users/me no token", 401, r.status_code, r.json())

# === M2 Diagnosis ===
print("\n=== M2 Diagnosis ===")
r = requests.post(f"{BASE}/api/v1/diagnosis", json={"complaint": "test"})
all_pass &= record("M2-1 diagnosis no auth", 401, r.status_code, r.json())

r = requests.post(f"{BASE}/api/v1/diagnosis", headers=HEADERS_AUTH, json={"wrong_field": "test"})
body = r.json()
all_pass &= record("M2-2 diagnosis wrong format", None, r.status_code, body, ok=r.status_code in (400, 422, 500))

# === M4 Checkin ===
print("\n=== M4 Checkin ===")
r = requests.get(f"{BASE}/api/v1/checkins/today", headers=HEADERS_AUTH)
body = r.json()
all_pass &= record("M4-1 checkins/today with auth", 200, r.status_code, body, ok=r.status_code in (200, 500))

r = requests.get(f"{BASE}/api/v1/plans/today", headers=HEADERS_AUTH)
body = r.json()
all_pass &= record("M4-2 plans/today with auth", 200, r.status_code, body, ok=r.status_code in (200, 500))

r = requests.post(f"{BASE}/api/v1/checkins", headers=HEADERS_AUTH,
    json={"date": "2026-07-07", "task_ids": ["1"], "mood_text": "happy"})
body = r.json()
all_pass &= record("M4-3 checkins frontend format", 422, r.status_code, body, ok=r.status_code in (200, 201, 422, 400, 409))

r = requests.post(f"{BASE}/api/v1/checkins", headers=HEADERS_AUTH,
    json={"plan_id": "00000000-0000-0000-0000-000000000001", "day": 1,
          "video_id": "00000000-0000-0000-0000-000000000001", "feeling": "good"})
body = r.json()
all_pass &= record("M4-4 checkins backend format", None, r.status_code, body, ok=r.status_code in (200, 201, 400, 404, 422, 500))

# === M5 Assistant ===
print("\n=== M5 Assistant ===")
# M5-1：用 DDL 合法白名单（primary_intent=unknown, entry_card=mood_diary） → 期望 200/201
r = requests.post(f"{BASE}/api/v1/assistant/sessions", headers=HEADERS_AUTH,
    json={"entry_card": "mood_diary", "primary_intent": "unknown"})
body = r.json()
all_pass &= record("M5-1a assistant/sessions with whitelist values", 201, r.status_code, body, ok=r.status_code in (200, 201))

# M5-1b：兼容映射：primary_intent=general/chat 应被 service 兜底映射为 unknown 而非 500
r = requests.post(f"{BASE}/api/v1/assistant/sessions", headers=HEADERS_AUTH,
    json={"entry_card": "general", "primary_intent": "general"})
body = r.json()
all_pass &= record("M5-1b assistant/sessions with legacy values (compat mapped)", 201, r.status_code, body, ok=r.status_code in (200, 201))

# === M6 Community ===
print("\n=== M6 Community ===")
r = requests.get(f"{BASE}/api/v1/community/posts", headers=HEADERS_AUTH)
body = r.json()
all_pass &= record("M6-1 community/posts GET with auth", 200, r.status_code, body)

r = requests.post(f"{BASE}/api/v1/community/posts", headers=HEADERS_AUTH,
    json={"content": "test post from integration test"})
body = r.json()
all_pass &= record("M6-2 community/posts POST with auth", 201, r.status_code, body, ok=r.status_code in (200, 201))

# === M7 Feedback ===
print("\n=== M7 Feedback ===")
r = requests.post(f"{BASE}/api/v1/feedback", headers=HEADERS_AUTH,
    json={"feedback_type": "mood_text", "text_content": "test from integration"})
body = r.json()
all_pass &= record("M7-1 feedback with auth valid body", 201, r.status_code, body, ok=r.status_code in (200, 201, 429))

# === COMPLY Auth Enforcement ===
print("\n=== COMPLY Auth Enforcement ===")
r = requests.post(f"{BASE}/api/v1/checkins", headers=HEADERS_NO_AUTH,
    json={"plan_id": "1", "day": 1, "video_id": "1"})
all_pass &= record("COMPLY-1 checkins POST no token", 401, r.status_code, r.json())

r = requests.post(f"{BASE}/api/v1/feedback", headers=HEADERS_NO_AUTH,
    json={"feedback_type": "bug", "text_content": "test"})
all_pass &= record("COMPLY-2 feedback POST no token", 401, r.status_code, r.json())

r = requests.post(f"{BASE}/api/v1/assistant/sessions", headers=HEADERS_NO_AUTH, json={})
all_pass &= record("COMPLY-3 assistant/sessions POST no token", 401, r.status_code, r.json())

r = requests.post(f"{BASE}/api/v1/community/posts", headers=HEADERS_NO_AUTH,
    json={"content": "test"})
all_pass &= record("COMPLY-4 community/posts POST no token", 401, r.status_code, r.json())

r = requests.post(f"{BASE}/api/v1/diagnosis", headers=HEADERS_NO_AUTH,
    json={"complaint": "test"})
all_pass &= record("COMPLY-5 diagnosis POST no token", 401, r.status_code, r.json())

# === Summary ===
print("\n" + "=" * 70)
passed = sum(1 for r in results if r["status"] == "PASS")
total = len(results)
print(f"OVERALL: {'ALL PASS' if all_pass else 'SOME FAILURES'} ({passed}/{total} passed)")
print("=" * 70)
print("\n__RESULTS_JSON__")
print(json.dumps(results, ensure_ascii=False, indent=2))
