"""M5 assistant 500 修复冒烟测试 (2026-07-07 19:00 UTC+8)。

复用 ``backend/scripts/test_mvp_api.py`` 的鉴权上下文：
- user_id: f255dff8-9f47-43a6-91c4-932b00c0447f
- base: http://127.0.0.1:8000

期望：所有 5 个用例都不再返回 500（500 是修复前的 bug 现象）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.auth.jwt_handler import sign_access_token  # noqa: E402

import requests  # noqa: E402

BASE = "http://127.0.0.1:8000"
TEST_USER_ID = "f255dff8-9f47-43a6-91c4-932b00c0447f"
TOKEN = sign_access_token(user_id=TEST_USER_ID)
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

cases = [
    ("M5-1a DDL legal whitelist", {"entry_card": "mood_diary", "primary_intent": "unknown"}),
    ("M5-1b legacy values (compat)", {"entry_card": "general", "primary_intent": "general"}),
    ("M5-1c legacy intent=chat + legacy card=checkin_done", {"entry_card": "checkin_done", "primary_intent": "chat"}),
    ("M5-1d completely unknown value (fallback)", {"entry_card": None, "primary_intent": "totally_garbage_xyz"}),
    ("M5-1e truly invalid entry_card (should reject 4xx)", {"entry_card": "bad_card_xyz", "primary_intent": "unknown"}),
    ("M5-1f primary_intent=diagnosis → module_redirect", {"entry_card": "smart_analyze", "primary_intent": "diagnosis"}),
]

all_pass = True
for name, body in cases:
    r = requests.post(f"{BASE}/api/v1/assistant/sessions", headers=H, json=body)
    ok = r.status_code in (200, 201, 400, 422)  # 不允许 500
    if name.startswith("M5-1e"):
        ok = r.status_code in (400, 422)
    elif name.startswith("M5-1a") or name.startswith("M5-1b") or name.startswith("M5-1c") or name.startswith("M5-1d") or name.startswith("M5-1f"):
        ok = r.status_code in (200, 201)
    flag = "PASS" if ok else "FAIL"
    all_pass &= ok
    print(f"[{flag}] {name} | status={r.status_code} | body={r.text[:160]}")

print()
print("=" * 70)
print(f"OVERALL: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
print("=" * 70)
sys.exit(0 if all_pass else 1)