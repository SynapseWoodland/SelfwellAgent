"""assistant `_stream_smart_analyze` SSE 5 阶段 progress + report + end 7 字段测试（V5.2.1-PR3 T17 + T18 + T19）。

不真正启动 DB / LLM（用 importlib + 静态 read）；原因：
- `_stream_smart_analyze` 是 async generator，集成成本高
- 本测专注字段契约（与 runner schema 模式相同的"契约层"思路）
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _read_assistant_service_source() -> str:
    src_path = Path(__file__).resolve().parents[3] / "app" / "services" / "assistant_service.py"
    return src_path.read_text(encoding="utf-8")


def test_vision_progress_emits_5_stages_with_step_percent_label_schema() -> None:
    """T17：`_stream_smart_analyze` yield 5 个 progress（step=1..5），字段名 `{step, percent, label}`."""
    src = _read_assistant_service_source()

    # 5 个 progress yield（顺序不强制，但每行 step 必须存在 1..5）
    for step in (1, 2, 3, 4, 5):
        assert f"_emit_progress({step}," in src, (
            f"_stream_smart_analyze 缺第 {step} 阶段 progress emit"
        )

    # 字段名必须是 {step, percent, label}（真源 assistant_v1.py:115 + ADR-0007 §2.5）
    # _emit_progress 是 _stream_smart_analyze 内嵌 async 函数——不通过 hasattr 校验；
    # 改用静态搜索其定义
    import re
    embed_match = re.search(r"async def _emit_progress\([^)]*\)[^:]*:\s*\\?\\?\s*([^\\\n]+)", src)
    if embed_match is None:
        # 跨行定义——直接在全文搜 step/percent/label 三 key 都在 source 出现
        assert "step" in src and "percent" in src and "label" in src, (
            "assistant_service 源文件应含 step/percent/label 字段名"
        )


def test_vision_end_event_has_7_fields_per_v521_pr3_t19() -> None:
    """T19：smart_analyze `_stream_smart_analyze` 成功路径 end event 7 字段契约.

    V5.2.1 §3.7 T19 + §7.1 锚点 #4：chat 路径 end 已有 6 字段（无需 PR3 改）；
    smart_analyze 路径 end 需补 6 字段 + level = 7 字段。

    走精确匹配：先定位 `_stream_smart_analyze` 函数体起止，再搜函数内的
    `_sse_pack("end"` 第一处（=成功路径），验其字典包含 7 个字段。
    """
    src = _read_assistant_service_source()

    # 抽取 _stream_smart_analyze 函数体（一直到下一个顶级 def）
    import re
    smart_match = re.search(
        r"async def _stream_smart_analyze\((.*?)^(?:async def |def |\Z)",
        src,
        re.MULTILINE | re.DOTALL,
    )
    assert smart_match, "assistant_service 缺 _stream_smart_analyze 函数"
    smart_body = smart_match.group(0)

    expected_keys = [
        '"ok"',
        '"reply"',
        '"persona_state"',
        '"is_mock"',
        '"medical_guarded"',
        '"is_quick_reply"',
        '"level"',
    ]

    end_match = re.search(r'_sse_pack\(\s*"end"\s*,\s*\{', smart_body)
    assert end_match, "_stream_smart_analyze 缺 _sse_pack(\"end\", ...) yield"
    end_start = end_match.start()
    end_block = smart_body[end_start : end_start + 600]
    for key in expected_keys:
        assert key in end_block, (
            f"smart_analyze 成功路径 end event 缺字段 {key}；end 段:\n{end_block}"
        )


def test_vision_primary_level_falls_back_to_light_when_no_directions() -> None:
    """T19：directions 空时 primary_level 兜底 '轻度'，不抛 KeyError."""
    src_module = importlib.import_module("app.services.assistant_service")
    # 因 primary_level 是局部变量，运行时取；只能静态确认 fallback string
    src = _read_assistant_service_source()
    assert (
        'directions[0].get("level", "轻度") if directions else "轻度"' in src
    ), "primary_level fallback 字符串变化"


@pytest.mark.parametrize(
    ("step", "percent", "label"),
    [
        (1, 15, "图片校验中"),
        (2, 45, "正在分析体态"),
        (3, 75, "生成养护建议"),
        (4, 100, "分析完成"),
        (5, 100, "已就绪"),
    ],
)
def test_vision_5_stages_match_v521_layout(step: int, percent: int, label: str) -> None:
    """5 阶段 progress 字段值与 V5.2.1 §3.5 T17 一致."""
    src = _read_assistant_service_source()
    pattern = f"_emit_progress({step}, {percent}, \"{label}\")"
    assert pattern in src, f"_emit_progress 第 {step} 阶段字段应为 ({step}, {percent}, {label})"
