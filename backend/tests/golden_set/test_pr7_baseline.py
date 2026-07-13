"""PR-7 deterministic Golden Set and route-baseline contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_ROOT = REPOSITORY_ROOT / "backend" / "tests" / "golden_set"
GOLDEN_SET = GOLDEN_ROOT / "golden_set_v2.yaml"
BASELINE = GOLDEN_ROOT / "_baselines" / "v2_baseline_2026-07-12.json"
ROUTES = GOLDEN_ROOT / "_baselines" / "v2_routes.txt"


def test_v2_golden_set_has_contiguous_ids_and_one_pinned_case() -> None:
    """Lock the ten-case GS-V2 numbering and the sole PINNED anchor."""
    document = yaml.safe_load(GOLDEN_SET.read_text(encoding="utf-8"))
    cases = document["cases"]

    assert [case["id"] for case in cases] == [
        f"GS-V2-{index:02d}" for index in range(1, 11)
    ]
    assert [case["id"] for case in cases if case.get("pinned")] == ["GS-V2-10"]
    assert all(case["real_data_anchors"] for case in cases)


def test_v2_baseline_is_zero_tolerance_and_all_passed() -> None:
    """Lock the accepted PR baseline summary."""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert baseline["total"] == 10
    assert baseline["passed"] == 10
    assert baseline["failed"] == 0
    assert baseline["tolerance"] == 0
    assert all(result["status"] == "pass" for result in baseline["results"])


def test_golden_eval_pr_mode_matches_existing_baseline() -> None:
    """Require a second PR-mode run to match the baseline exactly."""
    completed = subprocess.run(
        [sys.executable, "backend/scripts/run_golden_eval.py", "--mode", "pr"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout[completed.stdout.index("{") :])
    assert payload["baseline_matches"] is True
    assert payload["failed"] == 0


def test_v2_route_verifier_matches_openapi_snapshot() -> None:
    """Require the route verifier CLI to accept the checked-in snapshot."""
    completed = subprocess.run(
        [sys.executable, "backend/scripts/verify_sse_logs.py", "v2-routes"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "PASS v2-routes: 45 OpenAPI operations" in completed.stdout
    assert len(ROUTES.read_text(encoding="utf-8").splitlines()) == 45
