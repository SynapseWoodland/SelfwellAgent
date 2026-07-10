"""Vision level yield + yaml route 回填测试（V5.2.1-PR2 T13 + 落档）。"""

from __future__ import annotations

from pathlib import Path

import yaml


def test_vision_005_yaml_route_is_stream_smart_analyze_level() -> None:
    """VISION-005 route 已回填为 stream_smart_analyze_level（PR2 落档）."""
    yaml_path = (
        Path(__file__).resolve().parents[3] / "eval" / "golden_set_v1.yaml"
    )
    assert yaml_path.exists(), f"yaml 不在预期路径: {yaml_path}"
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("cases", [])
    vision_005 = next((c for c in cases if c.get("id") == "GN-ASSISTANT-VISION-005"), None)
    assert vision_005 is not None, "yaml 缺 GN-ASSISTANT-VISION-005"

    expected = vision_005.get("expected", {})
    assert expected.get("route") == "stream_smart_analyze_level", (
        f"VISION-005 route 期望 stream_smart_analyze_level，实为 {expected.get('route')!r}"
    )


def test_golden_yaml_no_residual_todo() -> None:
    """PR2 完成后，golden_set_v1.yaml 中 0 处 TODO 占位."""
    yaml_path = (
        Path(__file__).resolve().parents[3] / "eval" / "golden_set_v1.yaml"
    )
    content = yaml_path.read_text(encoding="utf-8")
    todo_count = content.count("TODO: from V4.1")
    assert todo_count == 0, (
        f"PR2 后应 0 处 TODO 占位，实为 {todo_count}；可能漏回填 VISION-005."
    )


def test_helper_module_exists_and_exports_build_photo_urls() -> None:
    """T14：app/services/_photo_urls.py 新建 + 导出 build_photo_urls."""
    from app.services import _photo_urls

    assert hasattr(_photo_urls, "build_photo_urls")
    import inspect
    assert inspect.iscoroutinefunction(_photo_urls.build_photo_urls)
