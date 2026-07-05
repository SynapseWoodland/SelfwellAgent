"""Prompts loader（Sprint 0 占位骨架）。

真源：coding-standards SKILL.md §一"Prompt 模板 ``prompts/``，禁止在节点内拼接"。

约定：
1. 所有 prompt 文件统一放到 ``app/prompts/*.yaml`` / ``*.prompt``
2. 内容含：``name``, ``version``, ``system``, ``user_template``, ``description``
3. Sprint 0 提供 1 个占位 prompt（M2 诊断系统），Sprint 2+ 替换为合规红线 1-7 hardcode 版
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.core.errors import PermanentError

_PROMPTS_DIR = Path(__file__).resolve().parent


class Prompt(BaseModel):
    """运行时 Prompt 表示。"""

    name: str
    version: str = "v1"
    description: str = ""
    system: str = ""
    user_template: str = ""


def prompts_dir() -> Path:
    """``app/prompts/`` 绝对路径。"""
    return _PROMPTS_DIR


@lru_cache(maxsize=64)
def load_prompt(name: str) -> Prompt:
    """加载 ``app/prompts/{name}.yaml`` 解析为 ``Prompt`` 对象。

    Args:
        name: 文件名（不含扩展名），如 ``diagnosis_system_v1``。

    Raises:
        PermanentError: 文件缺失 / YAML 解析失败 / schema 不匹配。

    """
    path = prompts_dir() / f"{name}.yaml"
    if not path.exists():
        # fallback: 允许 ``*.prompt`` 文件
        alt = prompts_dir() / f"{name}.prompt"
        if alt.exists():
            path = alt
        else:
            raise PermanentError(
                f"Prompt file not found: {path}",
                code="E_GENERAL_NOT_FOUND",
                http_status=500,
                file=str(path),
            )
    try:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise PermanentError(
            f"YAML parse error: {path}",
            code="E_GENERAL_INTERNAL_ERROR",
            http_status=500,
        ) from exc
    return Prompt(
        name=str(raw.get("name") or name),
        version=str(raw.get("version") or "v1"),
        description=str(raw.get("description") or ""),
        system=str(raw.get("system") or ""),
        user_template=str(raw.get("user_template") or ""),
    )


__all__ = ["Prompt", "load_prompt", "prompts_dir"]
