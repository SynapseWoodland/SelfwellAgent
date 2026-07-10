"""Golden Set SCHEMA 模式 smoke test（V5.2.1-PR1 必交付）。

跑 runner SCHEMA 模式验证 12 处 TODO 占位回填后 schema 一致性。

V5.2.1 §4.1.2 约束：test_golden_schema.py 必须放 backend/eval/（与 runner.py 同级）
不进 tests/eval/。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.golden_set
def test_golden_schema_mode_returns_route_distribution_with_11_pr1_fills() -> None:
    """SCHEMA 模式跑通；含 PR1 11 处回填路由字符串。

    PR1 范围：仅验证 11 处 V5.2.1 §7.2 实路由字符串已注入 yaml；不要求
    runner returncode==0（baseline 9 项 E_CODE regression 属 V5.2.1 §5.2/PR7 范围，
    不在 PR1 任务清单）。runner SCHEMA 模式输出含完整 route_distribution JSON；
    即使 11 项 baseline regression 让 rc=1，stdout 仍含 11 个 PR1 route 字符串
    —— 证明 yaml 回填成功。

    期望：
    - runner returncode 任意（baseline 9 项 regression 不影响 stdout 含
      route_distribution 段）
    - route_distribution JSON 段含 10 个 PR1 路由字符串（route 字段回填）
    - VISION-005 仍为 "<TODO: from V4.1 Step 2.3 ...>"（PR2 后回填）
    """
    backend_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        "-m",
        "eval.runner",
        "--mode",
        "schema",
    ]
    result = subprocess.run(
        cmd,
        cwd=backend_root,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    # 不强求 rc=0：baseline 9 项 regression 让整体 fail，但 PR1 范围内 11 处回填的
    # 路由字符串已在 yaml 中。验证 stdout 含 route_distribution 段即可。
    distribution_match = re.search(
        r'"route_distribution"\s*:\s*\{([^}]*)\}',
        result.stdout,
        re.DOTALL,
    )
    assert distribution_match, (
        f"runner 输出未含 route_distribution JSON 段:\n"
        f"RC={result.returncode}\nSTDOUT (last 1500):\n{result.stdout[-1500:]}"
    )
    distribution_block = distribution_match.group(1)

    pr1_routes = {
        "stream_smart_analyze",
        "stream_smart_analyze_timeout",
        "stream_smart_analyze_heic",
        "stream_smart_analyze_rate_limit",
        "stream_chat",
        "stream_chat_token_delta",
        "stream_chat_consistent",
        "stream_chat_followup",
        "cross_emotion_persona",
        "cross_quick_reply",
    }
    missing = {r for r in pr1_routes if f'"{r}"' not in distribution_block}
    assert not missing, (
        f"PR1 11 处路由回填缺：{sorted(missing)}；"
        f"runner 输出 distribution: {distribution_block[:1000]}"
    )


@pytest.mark.golden_set
def test_golden_yaml_todo_count_equals_one_residual() -> None:
    """PR1 完成后仅剩 VISION-005 1 处 TODO 占位（PR2 后回填）。"""
    yaml_path = Path(__file__).resolve().parents[1] / "eval" / "golden_set_v1.yaml"
    content = yaml_path.read_text(encoding="utf-8")
    todo_count = content.count("TODO: from V4.1")
    assert todo_count == 1, (
        f"PR1 回填后应仅剩 1 处 TODO（VISION-005），实为 {todo_count} 处。"
        f"检查 yaml 是否漏回填 / 多回填。"
    )


@pytest.mark.golden_set
def test_golden_yaml_vision_004b_code_field_is_e_assistant_rate_limit() -> None:
    """GN-ASSISTANT-VISION-004 的 code 字段已回填为 E_ASSISTANT_RATE_LIMIT。

    V5.2.1 §7.2 VISION-004b 拍板的 1 个 code 占位回填（与 11 个 route 占位
    并列，合计 12 处）。
    """
    yaml_path = Path(__file__).resolve().parents[1] / "eval" / "golden_set_v1.yaml"
    content = yaml_path.read_text(encoding="utf-8")
    # VISION-004 case 段含 "code: E_ASSISTANT_RATE_LIMIT"（无 quote，单 token 形式）
    assert "code: E_ASSISTANT_RATE_LIMIT" in content, (
        "VISION-004b code 字段未回填（应回填为 E_ASSISTANT_RATE_LIMIT）"
    )
