"""Selfwell 后端 AI Agent 服务（Sprint 0 骨架）。

包结构（与 SKILL.md §一/plan §3.1 对齐）：
- conf/      pydantic-settings 配置入口
- core/      loguru / trace / errors / retry
- errors/    业务错误码字典（``E_*`` 常量）
- db/        SQLAlchemy ORM + async session
- contracts/ NodeInput / NodeOutput 基类
- state/     AgentState TypedDict 顶层
- nodes/     LangGraph 节点实现
- tools/     LangChain BaseTool 实现
- agents/    LangGraph 子图编排（仅放图）
- rules/     硬规则 YAML + 纯 Python 解释器
- llm/       4 级降级链（Claude → GPT-4o → Qwen VL → DeepSeek-VL → 规则引擎）
- prompts/   Prompt loader
- storage/   对象存储抽象（MinIO / COS）
- notification/ 推送通道（4 端 + 邮件）
- auth/      JWT + 微信客户端
- api/       FastAPI 中间件 + v1 router（Sprint 1+）
"""

__version__ = "0.1.0"
