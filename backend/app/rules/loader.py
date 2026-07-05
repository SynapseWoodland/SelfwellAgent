"""硬规则 YAML loader（Sprint 0 骨架）。

真源：``docs/spec/facts-anchor.md`` §5 视频匹配权重（0.5*标签 + 0.3*时长 + 0.2*难度）
+ 各 ADR 规则定义。

约定：
- 所有业务规则 YAML 必须通过本模块 ``load_rule(name)`` 读取
- 允许散落 ``.yaml`` 加载（一次性常驻内存）
- 加载失败 raise ``PermanentError``（CI 可在更早阶段 catch）
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.core.errors import PermanentError


# ─────────────────────────────────────────────────────────────────────────────
# §一 Pydantic 模型（rule 顶层结构）
# ─────────────────────────────────────────────────────────────────────────────
class Rule(BaseModel):
    """单条规则的运行时表示。"""

    name: str
    type: str = "weight"  # weight / threshold / lookup
    weight: float | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class RuleSet(BaseModel):
    """规则集（含 N 条规则）。"""

    version: str = "1.0"
    source: str = ""
    description: str = ""
    rules: list[Rule] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# §二 loader（lru_cache 一次性缓存）
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_RULES_DIR = Path(__file__).resolve().parent


def rules_dir() -> Path:
    """默认 ``app/rules/*.yaml`` 目录。"""
    return _DEFAULT_RULES_DIR


@lru_cache(maxsize=64)
def load_rule(name: str) -> RuleSet:
    """加载 ``app/rules/{name}.yaml`` 并解析为 ``RuleSet``。

    Args:
        name: 文件名（不含扩展名），如 ``video_match``。

    Raises:
        PermanentError: 文件缺失 / YAML 解析失败 / schema 不匹配。

    """
    path = rules_dir() / f"{name}.yaml"
    if not path.exists():
        raise PermanentError(
            f"Rule file not found: {path}",
            code="E_GENERAL_NOT_FOUND",
            http_status=500,
            file=str(path),
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PermanentError(
            f"YAML parse error: {path}",
            code="E_GENERAL_INTERNAL_ERROR",
            http_status=500,
            error=str(exc),
        ) from exc
    if not isinstance(raw, dict):
        raise PermanentError(
            f"Rule root must be a mapping, got {type(raw).__name__}",
            code="E_GENERAL_INTERNAL_ERROR",
            http_status=500,
        )
    rules_raw = raw.get("rules") or []
    rules = [
        Rule(
            name=str(r.get("name", idx)),
            type=str(r.get("type", "weight")),
            weight=r.get("weight"),
            config=r.get("config", {}) or {},
            description=str(r.get("description", "")),
        )
        for idx, r in enumerate(rules_raw)
    ]
    return RuleSet(
        version=str(raw.get("version", "1.0")),
        source=str(raw.get("source", "")),
        description=str(raw.get("description", "")),
        rules=rules,
    )


__all__ = ["Rule", "RuleSet", "load_rule", "rules_dir"]
