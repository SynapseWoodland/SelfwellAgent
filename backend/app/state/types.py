"""AgentState TypedDict 顶层（Sprint 0 锁定）。

真源：coding-standards SKILL.md §四"State 必须 TypedDict，禁止 dict，禁止 Pydantic BaseModel"。

约定：
- 顶层字段在 Sprint 0 锁定（避免 Sprint 1+ 各自扩展产生 key 冲突）
- 后续 Sprint 只允许**追加新 key**；不允许删除 / 重命名现有 key
- 重名 / 重载 reducer 语义必须走 Annotated[T, reducer]
- 业务层在 /agents 子图里 **只用** NotRequired 字段做扩展
"""

from __future__ import annotations

import operator
from typing import Annotated, NotRequired, Required, TypedDict


class AgentContext(TypedDict):
    """Runtime 注入了的 context：trace_id / user_id 等。"""

    trace_id: Required[str]
    user_id: Required[str]
    request_id: Required[str]


class AgentState(TypedDict):
    """LangGraph Agent State 顶层（V1.3 锁定）。

    字段语义：
    - query: 用户当前 query（仅最新一条）
    - messages: 跨节点追加消息（用 add reducer 替代裸 list）
    - plan_id: 关联方案 ID（M3 流程）
    - report_id: 关联诊断报告（M2 流程）
    - history: 节点间状态增量；用 operator.add 累加
    - error: 错误码字符串（``E_*``）或 None
    """

    query: Required[str]
    messages: Annotated[Required[list[str]], operator.add]
    plan_id: NotRequired[str]
    report_id: NotRequired[str]
    history: Annotated[Required[list[dict[str, object]]], operator.add]
    error: Required[str | None]
    retry_count: Annotated[Required[int], lambda old, new: (old or 0) + (new or 0)]


__all__ = ["AgentContext", "AgentState"]
