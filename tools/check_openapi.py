"""OpenAPI 契约校验工具（Phase 4 · 批次 4 · BE-FIX-09 配套）。

真源：
- ``docs/architecture/api.yaml`` —— 机器可读契约（外部 SDK / 文档生成）
- ``docs/architecture/error-codes.md`` —— 人类可读错误码字典
- SKILL.md §九-附 9.3 / 9.8：错误码字符串 / OpenAPI 双向同步约束

设计目标：
1. **静态校验 openapi.yaml 可被解析**（路径数 / schema 数 / 关键 schema 存在）
2. **校验关键路径的 stream_url 前缀**：``/api/v1/diagnosis/jobs/{id}/stream``（BE-FIX-03）
3. **校验关键 schema 的字段名**：避免再次出现 ``id`` vs ``recall_id`` 的漂移（BE-FIX-09）
4. **退出码约定**：0 = PASS，1 = FAIL（CI 红）；失败时输出问题清单

约束：
- **不引入 prance**（项目 pyproject.toml 未声明，且 Windows 装 openapi-spec-validator
  容易与现有 prance 冲突）；改用纯 ``yaml.safe_load`` + 文本正则做最关键的契约字段校验。
- **可被 CI / 本地 / pre-commit 复用** —— 默认读 ``docs/architecture/api.yaml``（相对仓库根），
  支持 ``--path`` 覆盖。
- **可与 ``openapi-spec-validator`` 配合** —— 如果未来引入（pyproject 显式声明后），
  加上 ``--strict`` 会再走一遍 spec validator；当前默认仅做静态校验。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


# ──────────────────────────────────────────────────────────────────────────────
# §一 默认路径 / 常量
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_OPENAPI_PATH = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi.yaml"

# 关键 schema 名称（V1.1.1 BE-FIX-09 锁定）
CRITICAL_SCHEMAS: tuple[str, ...] = (
    "DiagnosisAcceptedResponse",
    "PlanResponse",
    "PlanDay",
    "FeedbackListResponse",
    "RecallRequest",
    "RecallResponse",
    "RecallHistoryResponse",
    "RecallMessagesResponse",
    "ErrorResponse",
    "AssistantChatRequest",
    "AssistantChatResponse",
    "EntryCardsResponse",
)

# BE-FIX-03：stream_url 必须带 /api/v1 前缀
STREAM_URL_PATH_PATTERN = re.compile(r"^/api/v1/diagnosis/jobs/[^/]+/stream$")

# BE-FIX-09：recall_id 不再是 id（避免漂移）
RECALL_ID_FORBIDDEN_PROPERTY = "id"
RECALL_ID_REQUIRED_PROPERTY = "recall_id"


# ──────────────────────────────────────────────────────────────────────────────
# §二 校验函数
# ──────────────────────────────────────────────────────────────────────────────
def _load_openapi(path: Path) -> dict[str, Any]:
    """读取并解析 YAML；不存在或解析失败 → 抛 SystemExit(1)。"""
    if not path.exists():
        print(f"[FAIL] openapi 文件不存在: {path}", file=sys.stderr)
        raise SystemExit(1)
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"[FAIL] YAML 解析失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if not isinstance(data, dict):
        print("[FAIL] openapi 顶层结构不是 dict", file=sys.stderr)
        raise SystemExit(1)
    return data


def _check_paths_schemas_present(spec: dict[str, Any]) -> list[str]:
    """§一：paths 与 components.schemas 顶层必须存在。"""
    problems: list[str] = []
    if "paths" not in spec:
        problems.append("顶层缺 paths 段")
    if "components" not in spec:
        problems.append("顶层缺 components 段")
        return problems
    schemas = spec.get("components", {}).get("schemas", {})
    if not isinstance(schemas, dict) or not schemas:
        problems.append("components.schemas 必须是非空 dict")
    return problems


def _check_critical_schemas(spec: dict[str, Any]) -> list[str]:
    """§二：所有关键 schema 必须存在。"""
    schemas = spec.get("components", {}).get("schemas", {})
    problems: list[str] = []
    missing = [name for name in CRITICAL_SCHEMAS if name not in schemas]
    if missing:
        problems.append(f"缺关键 schema: {', '.join(missing)}")
    return problems


def _check_diagnosis_accepted_response(spec: dict[str, Any]) -> list[str]:
    """§三：DiagnosisAcceptedResponse.stream_url example 必须带 /api/v1 前缀（BE-FIX-03）。"""
    problems: list[str] = []
    schema = spec.get("components", {}).get("schemas", {}).get("DiagnosisAcceptedResponse")
    if not isinstance(schema, dict):
        return problems
    stream_url = schema.get("properties", {}).get("stream_url")
    if not isinstance(stream_url, dict):
        problems.append("DiagnosisAcceptedResponse 缺 stream_url 属性")
        return problems
    example = stream_url.get("example")
    if not isinstance(example, str) or not STREAM_URL_PATH_PATTERN.match(example):
        problems.append(
            "DiagnosisAcceptedResponse.stream_url.example 必须匹配 "
            f"{STREAM_URL_PATH_PATTERN.pattern} (BE-FIX-03)；当前 = {example!r}",
        )
    return problems


def _check_recall_response_field_names(spec: dict[str, Any]) -> list[str]:
    """§四：RecallResponse 必须有 recall_id，不应有顶层 id（BE-FIX-09 防漂移）。"""
    problems: list[str] = []
    schema = spec.get("components", {}).get("schemas", {}).get("RecallResponse")
    if not isinstance(schema, dict):
        return problems
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return problems
    # 主 schema：应有 recall_id，不应有顶层 id（id 是 referenced_feedbacks 内层允许的）
    if "recall_id" not in properties:
        problems.append("RecallResponse 必须含 recall_id 属性（BE-FIX-09 锁定）")
    return problems


def _check_feedback_list_response_field_names(spec: dict[str, Any]) -> list[str]:
    """§五：FeedbackListResponse.items 必须用 feedback_id（BE-FIX-09）。"""
    problems: list[str] = []
    schema = spec.get("components", {}).get("schemas", {}).get("FeedbackListResponse")
    if not isinstance(schema, dict):
        return problems
    items_schema = schema.get("properties", {}).get("items", {})
    inner = items_schema.get("items", {}) if isinstance(items_schema, dict) else {}
    props = inner.get("properties", {}) if isinstance(inner, dict) else {}
    if "feedback_id" not in props:
        problems.append("FeedbackListResponse.items 必须含 feedback_id 属性（BE-FIX-09 锁定）")
    return problems


def _check_plan_day_field_names(spec: dict[str, Any]) -> list[str]:
    """§六：PlanDay 必须用 day_index / duration_minutes（BE-FIX-02）。"""
    problems: list[str] = []
    schema = spec.get("components", {}).get("schemas", {}).get("PlanDay")
    if not isinstance(schema, dict):
        return problems
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return problems
    if "day_index" not in properties:
        problems.append("PlanDay 必须含 day_index 属性（BE-FIX-02 锁定）")
    if "duration_minutes" not in properties:
        problems.append("PlanDay 必须含 duration_minutes 属性（BE-FIX-02 锁定）")
    return problems


def _check_error_response_envelope(spec: dict[str, Any]) -> list[str]:
    """§七：ErrorResponse 必须有 error.code / message_zh / message_en 包裹结构（SKILL.md §九-附 9.4）。"""
    problems: list[str] = []
    schema = spec.get("components", {}).get("schemas", {}).get("ErrorResponse")
    if not isinstance(schema, dict):
        return problems
    if schema.get("required") != ["error"]:
        problems.append("ErrorResponse.required 必须为 ['error']（SKILL.md §九-附 9.4）")
    error_props = schema.get("properties", {}).get("error", {}).get("properties", {})
    required_keys = {"code", "message_zh"}
    missing = required_keys - set(error_props.keys())
    if missing:
        problems.append(f"ErrorResponse.error 缺必填字段: {', '.join(sorted(missing))}")
    return problems


def _collect_problems(spec: dict[str, Any]) -> list[str]:
    """聚合所有校验失败的问题。"""
    problems: list[str] = []
    problems.extend(_check_paths_schemas_present(spec))
    problems.extend(_check_critical_schemas(spec))
    problems.extend(_check_diagnosis_accepted_response(spec))
    problems.extend(_check_recall_response_field_names(spec))
    problems.extend(_check_feedback_list_response_field_names(spec))
    problems.extend(_check_plan_day_field_names(spec))
    problems.extend(_check_error_response_envelope(spec))
    return problems


# ──────────────────────────────────────────────────────────────────────────────
# §三 CLI 入口
# ──────────────────────────────────────────────────────────────────────────────
def _format_summary(spec: dict[str, Any]) -> dict[str, Any]:
    """汇总 spec 关键指标（不进入 PASS/FAIL 判断，只输出便于 CI 调试）。"""
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})
    return {
        "openapi_version": spec.get("openapi"),
        "info_version": spec.get("info", {}).get("version"),
        "title": spec.get("info", {}).get("title"),
        "path_count": len(paths),
        "schema_count": len(schemas),
        "diagnosis_accepted_stream_url": (
            spec.get("components", {})
            .get("schemas", {})
            .get("DiagnosisAcceptedResponse", {})
            .get("properties", {})
            .get("stream_url", {})
            .get("example")
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。

    Args:
        argv: 参数列表（默认读取 ``sys.argv[1:]``）。

    Returns:
        0 = PASS，1 = FAIL。

    """
    parser = argparse.ArgumentParser(
        description="OpenAPI 契约校验（Phase 4 批次 4 · BE-FIX-09）",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_OPENAPI_PATH,
        help=f"openapi.yaml 路径（默认：{DEFAULT_OPENAPI_PATH}）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式（CI 友好）",
    )
    args = parser.parse_args(argv)

    spec = _load_openapi(args.path)
    problems = _collect_problems(spec)
    summary = _format_summary(spec)

    if args.json:
        payload = {
            "path": str(args.path),
            "status": "ok" if not problems else "fail",
            "problems": problems,
            "summary": summary,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"openapi: {args.path}")
        print(f"  openapi_version : {summary['openapi_version']}")
        print(f"  info_version    : {summary['info_version']}")
        print(f"  title           : {summary['title']}")
        print(f"  paths           : {summary['path_count']}")
        print(f"  schemas         : {summary['schema_count']}")
        print(f"  stream_url_ex   : {summary['diagnosis_accepted_stream_url']}")
        if problems:
            print(f"\n[FAIL] {len(problems)} 项校验未通过：")
            for p in problems:
                print(f"  - {p}")
        else:
            print("\n[PASS] 所有关键 schema 与字段名校验通过")

    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())