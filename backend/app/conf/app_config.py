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

``_PROJECT_ROOT_ENV``：解析到仓库根的 ``.env``，避免在 ``backend/`` 启动时找不到文件。
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根 .env：backend/app/conf/app_config.py → 上 2 层 = 仓库根
_PROJECT_ROOT_ENV: Path = Path(__file__).resolve().parents[2] / ".env"
_PROJECT_ROOT_ENV_STR: str = str(_PROJECT_ROOT_ENV)


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
        env_file=_PROJECT_ROOT_ENV_STR,
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

    model_config = SettingsConfigDict(env_file=_PROJECT_ROOT_ENV_STR, extra="ignore")

    url: str = Field(default="", alias="DATABASE_URL")
    sync_url: str = Field(default="", alias="DATABASE_URL_SYNC")


class RedisConfig(BaseSettings):
    """Redis 连接参数。"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        env_prefix="REDIS_",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    url: str = ""


class MinioConfig(BaseSettings):
    """MinIO 开发态对象存储。"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        env_prefix="MINIO_",
        extra="ignore",
    )

    endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    root_user: str = Field(default="minioadmin", alias="MINIO_ROOT_USER")
    root_password: str = Field(default="", alias="MINIO_ROOT_PASSWORD")
    bucket: str = "selfwell"
    secure: bool = False
    # 公网可访问的主机（供方舟 LLM 调用 MinIO presigned URL）。
    # 格式：host:port（如 192.168.1.100:9000 或 husenlin.tail61999e.ts.net:443）
    # 不含 scheme（http:// / https://），scheme 由 MINIO_SECURE 决定。
    # 注意：需与 MINIO_ENDPOINT 保持同端口（9000），否则 presigned URL 会失效。
    public_host: str = Field(default="", description="MinIO 公网访问 host:port（不含 scheme）")


class StorageConfig(BaseSettings):
    """对象存储段（MinIO / COS 二选一，由 STORAGE_PROVIDER 决定）。"""

    model_config = SettingsConfigDict(env_file=_PROJECT_ROOT_ENV_STR, extra="ignore")

    provider: str = "minio"  # minio / cos
    minio: MinioConfig = Field(default_factory=MinioConfig)


class LLMClientConfig(BaseSettings):
    """OpenAI 兼容 LLM 客户端统一配置（按 text / vision 能力分层）。

    全部走 OpenAI-compatible 接口（Doubao / GLM / Qwen VL / DeepSeek），无需各 SDK。

    真源：``.env`` §LLM 主备。

    降级链（文本）：
        - 主：DeepSeek Chat（``deepseek-chat``）— 性价比首选
        - 备：GLM-4-Flash（``glm-4-flash``）— 智谱开放平台，超低单价 SLA 稳
        - 末：静态文案兜底（``static-fallback``）

    字段命名约定：
        - 主文本：``LLM_PROVIDER`` / ``LLM_MODEL`` / ``LLM_BASE_URL`` / ``LLM_API_KEY``
        - 备文本：``BACKUP_LLM_PROVIDER`` / ``BACKUP_LLM_MODEL`` /
          ``BACKUP_LLM_BASE_URL`` / ``BACKUP_LLM_API_KEY``
        - 历史别名 ``API_KEY / MODEL / BASE_URL / BACKUP_API_KEY / BACKUP_MODEL /
          BACKUP_BASE_URL`` 保留向后兼容（``populate_by_name=True`` + alias 双向映射）。

    注意：多模态与文本 provider 分链路调用，避免纯文本模型接收图片输入。
    """

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        extra="ignore",
        populate_by_name=True,
    )

    # ── 主文本（DeepSeek Chat，primary） ──
    # LLM_* 为主命名；API_KEY/MODEL/BASE_URL 为历史 alias 兼容。
    provider: str = Field(default="openai", alias="LLM_PROVIDER")
    api_key: str = Field(default="", alias="LLM_API_KEY")
    model: str = Field(default="deepseek-chat", alias="LLM_MODEL")
    base_url: str = Field(default="https://api.deepseek.com/v1", alias="LLM_BASE_URL")

    # ── 备文本（GLM-4-Flash，backup） ──
    backup_provider: str = Field(default="openai", alias="BACKUP_LLM_PROVIDER")
    backup_api_key: str = Field(default="", alias="BACKUP_API_KEY")
    backup_model: str = Field(default="glm-4-flash", alias="BACKUP_MODEL")
    backup_base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        alias="BACKUP_BASE_URL",
    )

    # ── 多模态（Doubao Seedream 主 + Qwen VL 备） ──
    # 与文本链路隔离；多模态调用走 multimodal_chain.py。
    multi_api_key: str = Field(default="", alias="MULTI_API_KEY")
    multi_model: str = Field(default="doubao-seedream-5.0-lite", alias="MULTI_MODEL")
    multi_base_url: str = Field(default="", alias="MULTI_BASE_URL")

    backup_multi_api_key: str = Field(default="", alias="BACKUP_MULTI_API_KEY")
    backup_multi_model: str = Field(default="qwen-vl-max", alias="BACKUP_MULTI_MODEL")
    backup_multi_base_url: str = Field(default="", alias="BACKUP_MULTI_BASE_URL")

    # ── vision LLM 超时 ──
    # V4.1 Step 1.2 / V4.1.1 扩展：多模态 LLM 超时兜底（秒）。
    # rule-engine fallback 兜底在 vision_timeout_sec 后自动触发。
    vision_timeout_sec: float = Field(default=30.0, alias="VISION_TIMEOUT_SEC")

    # ── 通用参数 ──
    temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")
    max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    monthly_budget_yuan: int = Field(
        default=700, alias="LLM_MONTHLY_BUDGET_YUAN"
    )  # ¥700/月上限（facts-anchor §4）
    daily_budget_yuan: int = 40  # ¥40/天上限（facts-anchor §4）


class WechatConfig(BaseSettings):
    """微信小程序 + 开放平台。"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        extra="ignore",
        populate_by_name=True,
    )

    mp_appid: str = Field(default="", alias="WX_MP_APPID")
    mp_secret: str = Field(default="", alias="WX_MP_SECRET")
    mp_template_id: str = Field(default="", alias="WX_MP_TEMPLATE_ID")
    mp_template_keywords: str = Field(
        default="",
        alias="WX_MP_TEMPLATE_KEYWORDS",
    )  # 格式：打卡时间|打卡名称|任务说明|提醒时间


# ─────────────────────────────────────────────────────────────────────────────
# §0.5 CORS 段（ADR-0018：dev/staging 全开 *，prod 严格白名单）
# ─────────────────────────────────────────────────────────────────────────────
class CORSConfig(BaseModel):
    """CORS 配置（ADR-0018）。

    三档强制策略：
    - ``dev`` / ``staging``：``allow_origins=["*"]`` + ``allow_credentials=False`` +
      ``max_age=0``（每次重发 OPTIONS，改 origin 即时生效）
    - ``prod``：从 ``CORS_ORIGINS`` env 逗号分隔读白名单，**空则 fail-fast**

    通用配置（所有环境）：

    - ``allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]``
    - ``allow_headers=["*"]``
    - ``expose_headers=["X-Trace-ID","X-Request-ID","ETag"]``

    关键设计：

    1. ``allow_credentials=False``：JWT 走 Bearer Header，不需要 cookie；这样
       ``allow_origins=["*"]`` 不会被浏览器拒绝（CORS 规范要求 credentials=True 时禁止 ``*``）。
    2. ``expose_headers``：前端 SSE error 排查时能直接读 ``X-Trace-ID`` 反查后端日志。
    3. ``max_age=600``（prod）：浏览器 10 分钟内不重发 OPTIONS，prod 友好。
    4. ``prod fail-fast``：``APP_ENV=prod`` + ``CORS_ORIGINS=""`` → ``raise ValueError``，不静默。

    真源：``docs/architecture/adr/0018-cors-policy.md`` §3.1 / §3.2 / §3.5。
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    allowed_origins: list[str] = Field(
        default_factory=list,
        description="允许跨域的 origin 列表。prod 必须非空。",
    )
    allow_credentials: bool = Field(
        default=False,
        description="是否允许 cookie/credentials。MVP 固定 False（JWT Header 鉴权）。",
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        description="允许的 HTTP 方法。",
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: ["*"],
        description="允许的请求头；* 表示允许任意自定义头（如 X-Trace-ID）。",
    )
    expose_headers: list[str] = Field(
        default_factory=lambda: ["X-Trace-ID", "X-Request-ID", "ETag"],
        description="浏览器 JS 可读取的响应头（SSE 排查依赖 X-Trace-ID）。",
    )
    max_age_seconds: int = Field(
        default=0,
        ge=0,
        le=86400,
        description="preflight 缓存秒数；prod 600（10 分钟）；dev 0（每次重发）。",
    )

    @classmethod
    def from_env(
        cls,
        *,
        app_env: str,
        cors_origins_env: str,
    ) -> CORSConfig:
        """按 ADR-0018 §3.1 构造 CORS 配置。

        Args:
            app_env: 环境标识（dev / staging / prod）。
            cors_origins_env: ``CORS_ORIGINS`` 原始字符串，逗号分隔多个 origin。

        Returns:
            按 env 选定的 ``CORSConfig`` 实例。

        Raises:
            ValueError: ``app_env == "prod"`` 但 ``cors_origins_env`` 为空时抛出
                （ADR-0018 §3.1 prod fail-fast 约束）。

        """
        # normalize env
        env_norm = (app_env or "dev").strip().lower()

        # parse origins
        origins = [
            o.strip()
            for o in (cors_origins_env or "").split(",")
            if o and o.strip()
        ]

        if env_norm == "prod":
            if not origins:
                # ADR-0018 §3.1: prod 必须配白名单，缺失 → 启动失败（fail-fast）
                raise ValueError(
                    "APP_ENV=prod but CORS_ORIGINS is empty (ADR-0018 fail-fast). "
                    "Set CORS_ORIGINS env to a comma-separated origin list, e.g. "
                    "CORS_ORIGINS=https://app.selfwell.cn,https://admin.selfwell.cn"
                )
            return cls(
                allowed_origins=origins,
                allow_credentials=False,
                max_age_seconds=600,
            )

        # dev / staging / unknown env fallback：全开 *（fail-open，dev 阶段零摩擦）
        return cls(
            allowed_origins=["*"],
            allow_credentials=False,
            max_age_seconds=0,
        )


class JWTConfig(BaseSettings):
    """JWT 签名配置。"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        env_prefix="JWT_",
        extra="ignore",
    )

    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24h


class AliyunDMConfig(BaseSettings):
    """阿里云 DirectMail（邮件兜底）。"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        env_prefix="ALIYUN_DM_",
        extra="ignore",
    )

    access_key_id: str = ""
    access_key_secret: str = ""
    region: str = "cn-hangzhou"


class MonitoringConfig(BaseSettings):
    """Prometheus 监控段。"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        extra="ignore",
        populate_by_name=True,
    )

    prometheus_multiproc_dir: str = Field(
        default="/tmp/prom_multiproc",  # noqa: S108
        alias="PROMETHEUS_MULTIPROC_DIR",
    )
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")


class StorageCallbackConfig(BaseSettings):
    """对象存储回调签名。"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        env_prefix="STORAGE_CALLBACK_",
        extra="ignore",
    )

    secret: str = ""


class AuditConfig(BaseSettings):
    """合规审计伪 ID 加盐（HMAC-SHA256）。

    真源：ADR-0017 §3.3 + ``docs/architecture/error-codes.md`` 审计事件字段约束。

    说明：
    - ``audit_pseudo_salt`` 用于把 user_id 哈希成不可逆伪 ID（写入 audit log）
    - 默认空字符串 → 测试环境 fallback 用项目名做 salt（生产必须显式设置）
    - 生产部署应通过 env ``AUDIT_PSEUDO_SALT=$(openssl rand -hex 32)`` 注入
    """

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        env_prefix="AUDIT_",
        extra="ignore",
        populate_by_name=True,
    )

    pseudo_salt: str = Field(default="selfwell-default-audit-salt", alias="AUDIT_PSEUDO_SALT")


# ─────────────────────────────────────────────────────────────────────────────
# §三 顶层 AppConfig
# ─────────────────────────────────────────────────────────────────────────────
class AppConfig(BaseSettings):
    """顶层配置（pydantic-settings 自动 .env 注入）。

    实例化时应确保 ``backend/.env`` 或仓库根 ``.env`` 存在。
    """

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT_ENV_STR,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 通用 ──
    app_env: AppEnv = AppEnv.DEV
    log_level: str = "INFO"
    tz: str = "UTC"

    # ── 后端服务 ──
    # 本地 dev 让出 8000 给 Caddy 反代(infra/caddy/Caddyfile),uvicorn 退到 8001。
    # 生产(Dockerfile / docker-compose.yaml)走 8000,通过环境变量 BACKEND_PORT
    # 在容器内覆盖本默认值(.env / docker compose env)。
    # 验证: curl http://127.0.0.1:8001/api/v1/healthz
    backend_port: int = 8001
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
    audit: AuditConfig = Field(default_factory=AuditConfig)
    # ── CORS（ADR-0018） ──
    cors: CORSConfig = Field(
        default_factory=lambda: CORSConfig.from_env(
            app_env="dev",
            cors_origins_env="",
        )
    )

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
# CORS 段按 env 显式构造（fail-fast：prod + 空 CORS_ORIGINS → 启动期 raise）
import os as _os_for_cors  # noqa: E402

app_config: AppConfig = AppConfig()
app_config.cors = CORSConfig.from_env(
    app_env=str(_os_for_cors.getenv("APP_ENV", "dev")),
    cors_origins_env=_os_for_cors.getenv("CORS_ORIGINS", ""),
)


__all__ = [
    "AliyunDMConfig",
    "AppConfig",
    "AppEnv",
    "AuditConfig",
    "CORSConfig",
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
