"""
app_config — Selfwell 统一配置对象（Phase 0 stub）

设计原则（与 SKILL.md §十/§十一 对齐）：
- 所有外部调用（LLM / Redis / MySQL / COS）必须从本模块读取参数
- 禁止硬编码连接字符串或密钥
- Phase 0 为占位 stub；PR-F 接入 pydantic-settings 时仅修改本文件

配置来源优先级（未来实现）：
    1. 环境变量（pydantic-settings 自动读取）
    2. .env 文件（本地开发）
    3. 默认值（CI / 占位）
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM 调用参数。对应 SKILL.md §十。"""

    model_name: str = "gpt-4o"
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048

    @property
    def is_configured(self) -> bool:
        """是否已配置（API key 非空）。"""
        return bool(self.api_key)


@dataclass
class RedisConfig:
    """Redis 连接参数。"""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    ssl: bool = False


@dataclass
class DBConfig:
    """MySQL 连接参数。"""

    host: str = "localhost"
    port: int = 3306
    database: str = "selfwell"
    username: str = "root"
    password: str = ""
    pool_size: int = 10
    pool_recycle: int = 3600


@dataclass
class COSConfig:
    """对象存储（MinIO / S3 兼容）参数。"""

    endpoint: str = "localhost:9000"
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "selfwell"
    secure: bool = False


@dataclass
class AppConfig:
    """顶层配置聚合对象。"""

    llm: LLMConfig = field(default_factory=LLMConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    db: DBConfig = field(default_factory=DBConfig)
    cos: COSConfig = field(default_factory=COSConfig)


# 全局单例（模块级实例，所有 from app.conf.app_config import app_config 共享）
app_config: AppConfig = AppConfig()
