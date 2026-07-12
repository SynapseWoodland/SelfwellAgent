"""一次性 SSE 日志验证脚本(开发态临时使用)。

跑一次 诊断创建 → SSE 流,观察终端 + backend/logs/app.log 是否都能看到 4 条
diagnosis_sse_yielded(connected / queued / analyzing / ready),且无断尾。
"""
import sys
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
from app.auth.jwt_handler import sign_access_token  # noqa: E402

BASE = "http://127.0.0.1:8000"
USER = "f255dff8-9f47-43a6-91c4-932b00c0447f"
TOKEN = sign_access_token(user_id=USER)

# 1) 拿到或创建一个 report(用最简 body:不传 photos,只传 complaint,看后端如何处理)
print("[1] POST /api/v1/diagnosis ...")
r = httpx.post(
    f"{BASE}/api/v1/diagnosis",
    json={
        "photos": [
            {"object_key": "log_verify/fake.jpg", "body_part": "face", "format": "jpg", "size_bytes": 1024}
        ],
        "complaint": "log_verify",
    },
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=10.0,
)
print(f"    status={r.status_code} body={r.text[:200]}")
if r.status_code not in (200, 201):
    print("ABORT: create failed")
    sys.exit(1)

data = r.json()
report_id = data.get("data", {}).get("report_id") or data.get("report_id")
print(f"    report_id={report_id}")

# 2) 拉 SSE 流(短时)
print(f"[2] GET /api/v1/diagnosis/{report_id}/stream ...")
with httpx.stream(
    "GET",
    f"{BASE}/api/v1/diagnosis/{report_id}/stream",
    headers={"Authorization": f"Bearer {TOKEN}", "Accept": "text/event-stream"},
    timeout=10.0,
) as resp:
    print(f"    status={resp.status_code}")
    buf = []
    line_no = 0
    for line in resp.iter_lines():
        line_no += 1
        buf.append(line)
        if line_no <= 30:
            print(f"    [{line_no}] {line}")
        if line.startswith("data: done") or (line.startswith("data: ") and '"done"' in line):
            break
print(f"    total lines={line_no}")
