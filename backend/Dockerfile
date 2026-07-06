# =============================================================================
# Selfwell Backend · Dockerfile
#   - 多阶段构建：builder（uv sync）+ runtime（slim）
#   - 镜像：python:3.12-slim（匹配 pyproject.toml requires-python = ">=3.12"）
#   - 包名：selfwell-backend（hatchling 打包；only-include = backend/app + backend/eval）
#   - 非 root 用户运行（coding-standards SKILL §安全 · 最小权限原则）
# =============================================================================

# ───────────────────────────── Stage 1: builder ─────────────────────────────
FROM python:3.12-slim AS builder

# uv: Astral 官方安装（业界 2026 Python 共识，比 pip 快 10-100x）
# 注：原方案 COPY --from=ghcr.io/astral-sh/uv:latest 在 Windows + Docker Desktop
#     环境下 BuildKit 解析 ghcr.io 失败（ghcr.io:443 DNS 在 VM 内不可达）。
#     改用 Astral 官方独立安装脚本，源为 astral.sh（与官方文档一致），
#     并通过 UV_VERSION 钉版本，避免 latest 漂移。
ARG UV_VERSION=0.7.13
ENV UV_INSTALL_DIR=/usr/local/bin
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL "https://astral.sh/uv/${UV_VERSION}/install.sh" -o /tmp/uv-install.sh \
 && sh /tmp/uv-install.sh \
 && rm /tmp/uv-install.sh \
 && uv --version

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# 先 copy 锁文件，最大化层缓存
COPY pyproject.toml uv.lock* ./

# 安装运行时依赖（--no-dev 排除 pytest/ruff/mypy 等开发依赖）
RUN uv sync --frozen --no-install-project --no-dev

# 再 copy 源码 + 打包项目
COPY . /build
RUN uv sync --frozen --no-dev

# ───────────────────────────── Stage 2: runtime ─────────────────────────────
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # 后端默认监听（FastAPI / uvicorn）
    HOST=0.0.0.0 \
    PORT=8000

# 安装健康检查依赖（curl 即可，wget/cURL 都行；用 curl 是 Debian 默认）
# tini: PID 1 信号转发，优雅关闭 worker
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        curl \
        tini \
 && rm -rf /var/lib/apt/lists/*

# 从 builder 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 工作目录 + 仅 copy 运行时需要的目录
WORKDIR /app
COPY backend/ /app/backend/
COPY pyproject.toml /app/

# 非 root 用户（UID 10001，与 K8s runAsNonRoot 兼容）
RUN groupadd --system --gid 10001 selfwell \
 && useradd --system --uid 10001 --gid selfwell --no-create-home --shell /usr/sbin/nologin selfwell \
 && chown -R selfwell:selfwell /app
USER selfwell

EXPOSE 8000

# 健康检查：/healthz 是 Liveness 探针约定（FastAPI 标准做法）
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

# tini 接管 PID 1，信号转发给 uvicorn
ENTRYPOINT ["/usr/bin/tini", "--"]

# 4 worker × 2 thread 是 FastAPI 默认推荐（按 2 核 4G 配置）
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]