"""
app.conf — 统一配置入口

所有模块从本模块读取配置，禁止硬编码。
配置结构（Phase 0 stub，后续 PR-F 接入真实 pydantic-settings）：
- app_config.llm      — LLM 调用参数
- app_config.redis     — Redis 连接参数
- app_config.db        — MySQL 连接参数
"""

from app.conf.app_config import app_config

__all__ = ["app_config"]
