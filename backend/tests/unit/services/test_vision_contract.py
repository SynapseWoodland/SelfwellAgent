"""Vision contract 测试（V5.2.1-PR2 T13 + T15）。

V5.2.1 §4.2.2 E2-5：profile 6 字段 + level schema 校验。
"""

from __future__ import annotations

import importlib

import pytest
from pydantic import ValidationError


def test_diagnosis_direction_has_level_field_with_default() -> None:
    """T13：DiagnosisDirection.level 字段存在，默认值为「轻度」."""
    from app.llm.schemas import DiagnosisDirection

    fields = DiagnosisDirection.model_fields
    assert "level" in fields
    assert fields["level"].default == "轻度"


def test_diagnosis_direction_level_accepts_three_values() -> None:
    """T13：level 仅接受 「轻度 / 中度 / 重度」 三选一."""
    from app.llm.schemas import DiagnosisDirection

    for valid in ("轻度", "中度", "重度"):
        d = DiagnosisDirection(title="t", description="d", level=valid)
        assert d.level == valid

    with pytest.raises(ValidationError):
        DiagnosisDirection(title="t", description="d", level="未知")


def test_diagnosis_direction_level_omitted_uses_default() -> None:
    """T13：level 缺省时默认「轻度」（rule_engine fallback 友好)."""
    from app.llm.schemas import DiagnosisDirection

    d = DiagnosisDirection(title="t", description="d")
    assert d.level == "轻度"


def test_assistant_profile_sends_six_fields() -> None:
    """T15：assistant_service._stream_smart_analyze profile 段含 6 字段.

    不直接调用端到端（需 DB / LLM），改为静态导入 assistant_service 后
    校验其 ``profile`` 字段取值范围。
    """
    from app.services import assistant_service

    src = importlib.reload(assistant_service).__file__
    with open(src, "r", encoding="utf-8") as f:
        content = f.read()

    expected_fields = [
        "focus_parts",
        "intensity",
        "preferred_time",
        "sitting_hours",
        "age_range",
        "skin_type",
    ]
    for field in expected_fields:
        assert f'"{field}":' in content, (
            f"assistant_service._stream_smart_analyze profile 段缺字段: {field}"
        )


def test_user_model_has_skin_type_field() -> None:
    """T15：User 模型新增 skin_type 字段（对应 alembic 0006 + DDL)."""
    from app.db.models.user import User

    columns = {c.name for c in User.__table__.columns}
    assert "skin_type" in columns
    assert "age_range" in columns
    assert "focus_parts" in columns
    assert "intensity" in columns
    assert "preferred_time" in columns
    assert "sitting_hours" in columns
