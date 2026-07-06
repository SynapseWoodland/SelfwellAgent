# Selfwell Infra · 本地开发与部署说明

> 本目录是 Selfwell 后端的**基础设施**配置，基于 [`docs/data/data-dictionary.md`](../docs/data/data-dictionary.md) V1.1.2（11 张业务表）与 [`docs/architecture/mvp-tech-architecture.md`](../docs/architecture/mvp-tech-architecture.md) §8 部署架构生成。

---

## 目录结构

```
.
├── docker-compose.yaml          # 主编排：db + redis + minio + backend（prometheus 走 profile）
├── .env.example                 # 环境变量模板（cp .env.example .env）
├── backend/
│   └── Dockerfile               # uv-based 多阶段构建
├── db/
│   └── init/                    # PostgreSQL 初始化（按字典附录 I 拆分 5 段）
│       ├── 00-extensions.sql    # uuid-ossp + uuidv7() 函数（PG 15 兼容）
│       ├── 01-schema.sql        # 11 张业务表 DDL（含审计 4 字段）
│       ├── 02-indexes.sql       # 全部二级索引（部分 / GIN / 复合）
│       ├── 03-checks.sql        # 业务枚举 + 一致性 CHECK（≥32 条）
│       ├── 04-triggers.sql      # 3 个触发器（cache expires / report cache / 软删除联级）
│       └── 05-verify.sql        # 初始化完成自检（11 张表 / 3 触发器 / CHECK 生效）
└── infra/
    └── prometheus/
        ├── prometheus.yml       # 抓 backend /metrics（profile=monitoring 启动）
        └── rules.yaml           # 8 项告警规则（LLM 预算 / 降级 / 合规 / 安全）
```

---

## 快速开始

### 1. 准备 `.env`

```bash
cp .env.example .env
# 至少修改以下几项（开发环境默认值可跑）：
#   POSTGRES_PASSWORD  ·  Redis 密码项（开发环境留空，生产必填）
#   JWT_SECRET_KEY     ·  32 字节随机串：openssl rand -hex 32
#   ANTHROPIC_API_KEY  ·  Claude 主 LLM
#   OPENAI_API_KEY     ·  GPT-4o 备 1
```

### 2. 启动基础服务（DB + Redis + MinIO）

```bash
docker compose up -d db redis minio minio-init
# 等 healthcheck 全部 healthy（约 30s）
docker compose ps
```

`minio-init` 是 init container，会自动创建 `selfwell` bucket。

### 3. 启动后端

```bash
docker compose up -d --build backend
docker compose logs -f backend
# 看到 "Application startup complete" + "Uvicorn running on http://0.0.0.0:8000"
```

### 4. 验证 DB 初始化（可选）

```bash
docker compose exec db psql -U selfwell -d selfwell -f /docker-entrypoint-initdb.d/05-verify.sql
```

期望：
- **验证 1** 返回 11 行（11 张业务表）
- **验证 2** `chk_count ≥ 32`
- **验证 3** `trg_count = 3`

### 5. 启用 Prometheus（可选）

```bash
docker compose --profile monitoring up -d prometheus
# 访问 http://localhost:9090/targets
```

---

## 服务端口速查

| 服务 | 容器端口 | 宿主机端口 | 访问 |
|------|----------|------------|------|
| backend | 8000 | 8000 | http://localhost:8000 |
| backend healthz | 8000 | 8000 | http://localhost:8000/healthz |
| backend metrics | 8000 | 8000 | http://localhost:8000/metrics |
| PostgreSQL | 5432 | 5432 | `psql -h localhost -U selfwell -d selfwell` |
| Redis | 6379 | 6379 | `redis-cli -h localhost` |
| MinIO API | 9000 | 9000 | http://localhost:9000 |
| MinIO Console | 9001 | 9001 | http://localhost:9001 (`minioadmin` / 你设的密码) |
| Prometheus | 9090 | 9090 | http://localhost:9090（profile=monitoring） |

---

## 常见操作

### 进 DB 跑 SQL

```bash
docker compose exec db psql -U selfwell -d selfwell
```

### 重置全部数据（⚠ 销毁卷）

```bash
docker compose down -v
docker compose up -d
```

### 仅重启后端（不重建 DB）

```bash
docker compose restart backend
# 或带新代码：
docker compose up -d --build backend
```

### 看后端日志

```bash
docker compose logs -f backend --tail=200
```

### 跑 Alembic 迁移（如未来引入）

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic revision --autogenerate -m "add xxx"
```

---

## 与数据字典附录 I 的对应关系

| 数据字典章节 | 对应文件 | 备注 |
|--------------|----------|------|
| 附录 I §I.0.3 UUID v7 函数 | `db/init/00-extensions.sql` | PG 15 自定义 + PG 18 内置幂等 |
| 附录 I §I.1 11 张表 DDL | `db/init/01-schema.sql` | 含 4 个延迟 FK（feedback ↔ ai_messages / ai_sessions ↔ feedback/recall） |
| 附录 I §I.2 全部索引 | `db/init/02-indexes.sql` | init-only 不使用 CONCURRENTLY（事务内） |
| 附录 I §I.3 CHECK 约束 | `db/init/03-checks.sql` | 故意不加的 5 个见附录 C.8 注释 |
| 附录 I §I.4 触发器 | `db/init/04-triggers.sql` | 仅 3 个（audit 触发器取消，见附录 E） |
| 附录 I §I.5 验证清单 | `db/init/05-verify.sql` | 8 项验证 |

---

## 与 `mvp-tech-architecture.md` §8 的对应关系

| 架构章节 | docker-compose 实现 |
|----------|---------------------|
| §8.1 backend（8000） | `backend` 服务（uvicorn 4 worker + tini PID 1） |
| §8.1 db（PG 15） | `db` 服务（PG 18-alpine，uuidv7() 内置） |
| §8.1 redis（6379） | `redis` 服务（appendonly + maxmemory 256MB） |
| §8.1 minio（9000/9001） | `minio` + `minio-init`（自动建 bucket） |
| §10.3 Prometheus 监控 | `prometheus` 服务（profile=monitoring） |
| §8.2 生产建议 | 见 `infra/production/` 后续文件（待补 K8s manifest） |

---

## 已知限制 / 待办

- [ ] Celery Beat 服务（auto_day7/14/21 主动回忆）当前**未启动**，需手动触发或后续加 `celery-beat` 服务
- [ ] Grafana + Alertmanager（§10.3 告警链路）当前**未集成**
- [ ] pgwatch2 / postgres-exporter **未启用**（mvp-tech-architecture §10.3 监控扩展）
- [ ] 生产 K8s manifest 待补（§8.2 "腾讯云容器服务"）
- [ ] pg_cron / pg_partman 等扩展未启用（MVP 不需要分区表）