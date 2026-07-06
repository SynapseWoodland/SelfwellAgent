"""app_config — Selfwell 统一配置对象（Sprint 0 pydantic-settings 版）。

设计真源：
- ``.env.example``（根目录，唯一环境变量字典）
- ``docker-compose.yaml`` §backend env_file + ``x-common-env``
- ``docs/architecture/mvp-tech-architecture.md`` §配置

约定：
- 字段名严格对齐 ``.env`` 键（全大写）；下方 Field alias 写法保留向后兼容
- 禁止硬编码连接字符串 / 密钥 / 阈值
- ``is_configured`` 按段判定（哪一段配齐了哪些 secret）

Sprint 0 落地：字段全集一次性补齐（POSTGRES / REDIS / LLM 4 级 / WX / JWT / MONITORING /
NOTIFICATION / STORAGE / DirectMail 等）；后续 Sprint 可只追加。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# §一 枚举（避免散落字符串）
# ─────────────────────────────────────────────────────────────────────────────
class AppEnv(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


# ─────────────────────────────────────────────────────────────────────────────
# §二 子配置：每段独立
# ─────────────────────────────────────────────────────────────────────────────
class PostgresConfig(BaseSettings):
    """PostgreSQL 连接参数（与 .env 的 POSTGRES_* 一致）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POSTGRES_",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = "localhost"
    port: int = 5432
    db: str = "selfwell"
    user: str = "selfwell"
    password: str = ""
    pool_size: int = 10
    pool_recycle: int = 3600


class DatabaseUrlConfig(BaseSettings):
    """DSN 字符串（与 .env 的 DATABASE_URL / DATABASE_URL_SYNC 一致）。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    url: str = Field(default="", alias="DATABASE_URL")
    sync_url: str = Field(default="", alias="DATABASE_URL_SYNC")


class RedisConfig(BaseSettings):
    """Redis 连接参数。"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="REDIS_", extra="ignore")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    url: str = ""


class MinioConfig(BaseSettings):
    """MinIO 开发态对象存储。"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MINIO_", extra="ignore")

    endpoint: str = "localhost:9000"
    root_user: str = Field(default="minioadmin", alias="MINIO_ROOT_USER")
    root_password: str = Field(default="", alias="MINIO_ROOT_PASSWORD")
    bucket: str = "selfwell"
    secure: bool = False


class StorageConfig(BaseSettings):
    """对象存储段（MinIO / COS 二选一，由 STORAGE_PROVIDER 决定）。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    provider: str = "minio"  # minio / cos
    minio: MinioConfig = Field(default_factory=MinioConfig)


class LLMClientConfig(BaseSettings):
    """OpenAI 兼容 LLM 客户端统一配置（4 级降级链）。

    全部走 OpenAI-compatible 接口（Doubao / GLM / Qwen VL / DeepSeek），无需各 SDK。

    真源：``.env`` §LLM 主备。

    降级链：
        1. 主多模态（Doubao Seedream）：MULTI_*（vision / image generation）
        2. 备多模态（Qwen VL）：BACKUP_MULTI_*（vision / image generation）
        3. 备文本（DeepSeek VL）：BACKUP_*（text）
        4. 主文本（GLM）：API_KEY / MODEL / BASE_URL（text only，非多模态时兜底）

    注意：主文本（GLM）放在最末，因为其 base_url 与主多模态（Doubao）相同，
    共享 Ark API 额度；在多模态模型全部失败后才降级到纯文本。
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 主多模态（Doubao Seedream）
    multi_api_key: str = Field(default="", alias="MULTI_API_KEY")
    multi_model: str = Field(default="doubao-seedream-5.0-lite", alias="MULTI_MODEL")
    multi_base_url: str = Field(default="", alias="MULTI_BASE_URL")

    # 主文本（GLM，Ark）
    api_key: str = Field(default="", alias="API_KEY")
    model: str = Field(default="glm-5.2", alias="MODEL")
    base_url: str = Field(default="", alias="BASE_URL")

    # 备多模态（Qwen VL）
    backup_multi_api_key: str = Field(default="", alias="BACKUP_MULTI_API_KEY")
    backup_multi_model: str = Field(default="qwen-vl-max", alias="BACKUP_MULTI_MODEL")

    # 备文本（DeepSeek VL）
    backup_api_key: str = Field(default="", alias="BACKUP_API_KEY")
    backup_model: str = Field(default="deepseek-vl", alias="BACKUP_MODEL")
    backup_base_url: str = Field(default="https://api.deepseek.com/v1", alias="BACKUP_BASE_URL")

    # 通用参数
    temperature: float = 0.7
    max_tokens: int = 2048
    monthly_budget_yuan: int = 700  # ¥700/月上限（facts-anchor §4）
    daily_budget_yuan: int = 40  # ¥40/天上限（facts-anchor §4）


class WechatConfig(BaseSettings):
    """微信小程序 + 开放平台。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mp_appid: str = ""
    mp_secret: str = ""
    mp_template_id: str = ""


class JWTConfig(BaseSettings):
    """JWT 签名配置。"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="JWT_", extra="ignore")

    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24h


class AliyunDMConfig(BaseSettings):
    """阿里云 DirectMail（邮件兜底）。"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALIYUN_DM_", extra="ignore")

    access_key_id: str = ""
    access_key_secret: str = ""
    region: str = "cn-hangzhou"


class MonitoringConfig(BaseSettings):
    """Prometheus 监控段。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    prometheus_multiproc_dir: str = "/tmp/prom_multiproc"  # noqa: S108
    enable_metrics: bool = True


class StorageCallbackConfig(BaseSettings):
    """对象存储回调签名。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STORAGE_CALLBACK_",
        extra="ignore",
    )

    secret: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# §三 顶层 AppConfig
# ─────────────────────────────────────────────────────────────────────────────
class AppConfig(BaseSettings):
    """顶层配置（pydantic-settings 自动 .env 注入）。

    实例化时应确保 ``backend/.env`` 或仓库根 ``.env`` 存在。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 通用 ──
    app_env: AppEnv = AppEnv.DEV
    log_level: str = "INFO"
    tz: str = "UTC"

    # ── 后端服务 ──
    backend_port: int = 8000
    uvicorn_workers: int = 4

    # ── 业务段 ──
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    db_urls: DatabaseUrlConfig = Field(default_factory=DatabaseUrlConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    llm: LLMClientConfig = Field(default_factory=LLMClientConfig)
    wechat: WechatConfig = Field(default_factory=WechatConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    aliyun_dm: AliyunDMConfig = Field(default_factory=AliyunDMConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    storage_callback: StorageCallbackConfig = Field(default_factory=StorageCallbackConfig)

    # ─────────────────────────────────────────────────────────────────────────
    # §四 is_configured：按段判定（哪一段配齐了哪些 secret）
    # ─────────────────────────────────────────────────────────────────────────
    @property
    def is_postgres_configured(self) -> bool:
        return bool(self.postgres.password)

    @property
    def is_redis_configured(self) -> bool:
        return bool(self.redis.password or self.redis.url)

    @property
    def is_llm_configured(self) -> bool:
        return any(
            (
                self.llm.multi_api_key,
                self.llm.backup_multi_api_key,
                self.llm.backup_api_key,
                self.llm.api_key,
            )
        )

    @property
    def is_wechat_configured(self) -> bool:
        return bool(self.wechat.mp_appid and self.wechat.mp_secret)

    @property
    def is_jwt_configured(self) -> bool:
        return len(self.jwt.secret_key) >= 32

    @property
    def is_storage_configured(self) -> bool:
        return bool(self.storage.minio.root_password)

    def is_configured(
        self,
        section: Literal[
            "postgres",
            "redis",
            "llm",
            "wechat",
            "jwt",
            "storage",
            "all",
        ] = "all",
    ) -> bool:
        """按段判定是否配齐。"""
        mapper: dict[str, bool] = {
            "postgres": self.is_postgres_configured,
            "redis": self.is_redis_configured,
            "llm": self.is_llm_configured,
            "wechat": self.is_wechat_configured,
            "jwt": self.is_jwt_configured,
            "storage": self.is_storage_configured,
        }
        if section == "all":
            return all(mapper.values())
        return mapper[section]


# ─────────────────────────────────────────────────────────────────────────────
# §五 全局单例
# ─────────────────────────────────────────────────────────────────────────────
app_config: AppConfig = AppConfig()


__all__ = [
    "AliyunDMConfig",
    "AppConfig",
    "AppEnv",
    "DatabaseUrlConfig",
    "JWTConfig",
    "LLMClientConfig",
    "MinioConfig",
    "MonitoringConfig",
    "PostgresConfig",
    "RedisConfig",
    "StorageCallbackConfig",
    "StorageConfig",
    "WechatConfig",
    "app_config",
]
