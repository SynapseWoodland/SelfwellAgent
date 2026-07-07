# Selfwell 自愈 · AI 智能健康陪伴

> **V1.3 MVP（2026-07-06）** · iOS APP（Flutter）+ 微信小程序 · 1 人 + AI 加速
> 当前 HEAD：`36dca24`（25 commit 落库，详见 `docs/checklist-0706.md`）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Flutter](https://img.shields.io/badge/Flutter-3.22-blue.svg)](https://flutter.dev/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> 「慢慢自律，慢慢健康，慢慢成为更好的自己」
> 无焦虑品牌 · 不打分 · 不评判 · 不对比

---

## 🌟 这是什么

**Selfwell 自愈** 是一个 AI 驱动的智能健康陪伴应用，专注**面部+头皮+肩颈+体态+久坐+生活方式**六大养护方向，用全网视频匹配 + 21 天轻自律闭环，让你慢慢变好。

**核心闭环**：AI 联合诊断 → 全网视频匹配 → 21 天打卡 → 治愈系轻社区

---

## ✨ 核心特性

- 🤖 **AI 多模态联合诊断** —— Claude Sonnet + GPT-4o + Qwen VL + DeepSeek-VL 4 级降级链
- 🎯 **全网视频匹配** —— 0.5 标签匹配 + 0.3 时长 + 0.2 难度（Jaccard 算法）
- 📅 **21 天轻自律闭环** —— 1-7 / 8-14 / 15-21 三阶段递进
- 💬 **智能管家对话主页** —— 4 状态机（warm / neutral / slight_hug / medical_guarded）
- 📔 **心情日记 + 多部位反馈** —— 4 种 feedback_type 完全可选
- 🌸 **主动回忆** —— Day 7/14/21 触发，与过去的自己对话
- 🎴 **抱抱卡分享** —— 第 7/14/21 天自动生成
- 🌳 **蜕变广场** —— 无焦虑、无攀比、纯治愈的轻社区

---

## 🏗️ 技术架构

### 后端（Python 3.12 + FastAPI）

| 技术 | 用途 |
|---|---|
| **FastAPI** | Web 框架（含 SSE 流式响应） |
| **SQLAlchemy 2.0 + asyncpg** | PostgreSQL 18 ORM |
| **Pydantic 2** | 配置 / 数据校验 |
| **LangChain / LangGraph** | Agent 编排 + 4 级 LLM 降级 |
| **Redis 7** | 缓存 / 限流 / Session |
| **MinIO** | 对象存储（照片 / 海报；生产由 `STORAGE_PROVIDER=cos` 切到腾讯云 COS） |
| **Loguru** | 结构化日志 |
| **Alembic** | 数据库迁移（基线版本 `0001_initial_v13_locked.py`） |

### 客户端

| 平台 | 技术 | 状态 |
|---|---|---|
| **iOS APP** | Flutter 3.22 | ✅ SF1-SF5 已落库（`469578b`） |
| **微信小程序** | 微信原生 + TypeScript | ✅ SF1-SF5 已落库（`be7d5f7` → `540b241`） |

---

## 🚀 快速启动

### 前置依赖

- Python 3.12 + [uv](https://docs.astral.sh/uv/)（`pip install uv`）
- Docker Desktop（PostgreSQL 18 / Redis 7 / MinIO 一键起）
- Flutter 3.22+（仅调试 iOS APP 时需要）
- 微信开发者工具（仅调试小程序时需要）

### 1. 克隆与安装

```bash
git clone https://github.com/<yourname>/selfwell-agent.git
cd selfwell-agent
uv sync --all-extras
cp .env.example .env       # 然后填密钥（见下表）
```

`.env` 必填项（其余可保留 dev 默认值）：

| 变量 | 说明 | 是否可空 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude Sonnet 主 LLM（推荐） | 留空则走降级链 |
| `OPENAI_API_KEY` | GPT-4o 备 1 | 可空 |
| `DASHSCOPE_API_KEY` | Qwen VL 备 2 | 可空 |
| `DEEPSEEK_API_KEY` | DeepSeek-VL 备 3 | 可空 |
| `WX_MP_APPID` / `WX_MP_SECRET` | 微信小程序登录 | 本地 mock 可空 |
| `JWT_SECRET_KEY` | 32+ 字节随机串（`openssl rand -hex 32`） | dev 默认值即可 |

### 2. 启动基础服务栈（PostgreSQL / Redis / MinIO）

```bash
docker compose up -d db redis minio minio-init
# 健康检查
docker compose ps
```

容器自动建表（`db/init/00-*` → `04-*` 共 5 段 SQL，含 11 表 / 32 checks / 3 triggers / 72 indexes）。MinIO bucket `selfwell` 由 `minio-init` 自动创建。

### 3. 启动 Backend

> ⚠️ **必须从仓库根目录启动**，否则 `from app.xxx` 找不到包。

```bash
# 方式 A：直接 uvicorn（推荐开发）
uv run uvicorn backend.app.main:app --reload --port 8000

# 方式 B：带 host 监听（小程序 / 局域网调试）
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

启动成功标志：

```
INFO     Application startup complete
INFO     Uvicorn running on http://0.0.0.0:8000
```

冒烟：

| URL | 用途 |
|---|---|
| http://localhost:8000/healthz | 三段探针（liveness / readiness / startup） |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/metrics | Prometheus 抓取（`ENABLE_METRICS=true` 时） |

> **不要**用 `python -c "import backend.app.main"` 冒烟 —— 根目录执行时 `import app.xxx` 找不到模块；用 `uvicorn` 启动 + 访问 `/healthz` 才是正确冒烟路径。

### 4. 启动小程序（mp-selfwell）

```bash
# 1. 打开微信开发者工具 → 导入项目
#    项目目录：apps/mp-selfwell/
#    AppID：apps/mp-selfwell/project.config.json 中已有 wx9967b7cc83336b6f
#
# 2. 工具 → 构建 npm（首次）
#
# 3. 微信开发者工具 → 设置 → 代理：
#    不勾选"使用系统代理"（避免被 Charles / Fiddler 劫持）
#
# 4. 调试器 Console 看 wx.request 是否走通 http://localhost:8000
```

> 微信开发者工具默认走 `localhost`，与本地 backend 直连；如果用真机预览，需将 `apps/mp-selfwell/miniprogram/utils/config.ts` 的 `BASE_URL` 改为局域网 IP 并在 mp 后台加白名单。

### 5. 启动 Flutter（flutter_app）

```bash
cd apps/flutter_app
flutter pub get
flutter run -d ios            # iOS 模拟器 / 真机
flutter test                 # 跑 widget + golden tests
```

> 本仓库 **未提供** Android 平台配置文件，Flutter 端 MVP 仅 iOS（与 `docs/plan/mvp-implementation-plan.md` 对齐）。

### 6. 启动监控栈（可选）

```bash
docker compose --profile monitoring up -d prometheus
# Grafana 暂未接入（MVP 阶段）
```

---

## 📂 项目结构

```
selfwell-agent/
├── backend/                        # Python 后端（FastAPI）
│   ├── app/
│   │   ├── api/v1/                 # REST 路由（auth_v1 / users_v1 / diagnosis_v1 / plans_v1 / business_v1）
│   │   ├── services/               # 业务服务层（auth / users / diagnosis / video_match / plan /
│   │   │                           #   checkin / assistant / feedback / community / recall / share）
│   │   ├── agents/                 # LangGraph Agent 编排
│   │   ├── nodes/                  # Agent 节点
│   │   ├── rules/                  # 业务规则（视频匹配 / 限流阈值等 YAML）
│   │   ├── prompts/                # LLM Prompt 模板
│   │   ├── db/models/              # SQLAlchemy ORM（11 张业务表）
│   │   ├── storage/                # 对象存储抽象（base / minio_impl / cos_impl）
│   │   ├── llm/                    # LLM 客户端 + fallback_chain + mock_doubles
│   │   ├── notification/           # 推送通道（wx_subscribe / apns / fcm）
│   │   ├── auth/                   # 微信登录 wechat_client
│   │   ├── contracts/              # Pydantic DTO
│   │   ├── errors/                 # 错误码表（codes.py）
│   │   ├── conf/                   # 统一配置 app_config
│   │   ├── core/                   # log / trace / retry / result / errors
│   │   └── main.py                 # FastAPI 入口（3 中间件 + lifespan）
│   ├── alembic/                    # 迁移（基线 0001_initial_v13_locked.py）
│   ├── tests/                      # pytest + bdd + load + golden + eval + e2e
│   ├── eval/                       # Eval Runner
│   ├── Dockerfile
│   └── alembic.ini
├── apps/                           # 客户端
│   ├── flutter_app/                # Flutter iOS APP（SF0-SF5）
│   │   ├── lib/{core,pages,widgets}/
│   │   ├── test/                   # widget + golden + sse_backoff
│   │   └── integration_test/
│   └── mp-selfwell/                # 微信小程序
│       ├── miniprogram/
│       │   ├── pages/              # login / home / checkin / diagnosis-* / plan / community / recall-* / share-* / profile / assistant-home / splash
│       │   ├── components/         # progress-ring / sse-progress / persona-bubble / ack-bubble / image-uploader / error-toast / task-card
│       │   ├── utils/              # request / config / push-payload / poster / error-code / subscribe
│       │   ├── data/ack-pool.ts    # 30 条心情管家 ACK 池
│       │   └── assets/tabbar/
│       └── tests/                  # sf1 screenshot / smoke
├── packages/                       # 跨端共享
│   ├── design-tokens.json          # 颜色 / 字号 / 间距 token
│   ├── lint-rules/                 # lint 规则集（含禁用色 #FF4D4F）
│   └── api-types/
│       ├── ts/                     # 双端共享 api.ts（M1-M10 全 DTO）
│       └── dart/                   # Flutter stub
├── infra/
│   ├── prometheus/                 # prometheus.yml + rules.yaml
│   └── README.md
├── db/init/                        # 5 段初始化 SQL（00 → 04）
├── .github/workflows/              # backend-ci.yml
├── pyproject.toml                  # 依赖 + Lint + mypy 配置（hatchling 打包）
├── docker-compose.yaml             # db / redis / minio / minio-init / [prometheus]
├── .env.example
└── README.md                       # 你正在读的
```

> `docs/` 路径在 `.gitignore` 中被忽略，**不随仓库公开**。商业敏感信息（PRD / SPEC / ADR）仅本地保留。
>
> 仓库根目录目前没有 `scripts/` 顶层目录；调试脚本随各端落地（`apps/mp-selfwell/tests/`、`apps/flutter_app/scripts/`、`backend/` 各含自己的脚本）。
>
> 调试指导书见 `docs/debug/`（本地不公开）。

---

## 📋 业务模块（M1-M11）

| ID | 模块 | 后端 | 小程序 | Flutter |
|---|---|---|---|---|
| M1 | 极简登录 / 用户档案 | ✅ `5a35dda` | ✅ SF1 | ✅ SF1 |
| M2 | AI 多模态联合诊断 | ✅ `92e696c` | ✅ SF2 | ✅ SF2 |
| M3 | 21 天方案生成 | ✅ `92e696c` | ✅ SF2 | ✅ SF2 |
| M4 | 每日打卡闭环 | ✅ `e16a655` | ✅ SF1 | ✅ SF1 |
| M5 | 智能管家对话主页 | ✅ `e16a655` | ✅ SF3 | ✅ SF3 |
| M6 | 蜕变广场 | ✅ `1c5db1e` | ✅ SF4 | ✅ SF4 |
| M7a | 心情日记 | ✅ `e16a655` | ✅ SF3 | ✅ SF3 |
| M7b | 多部位反馈 | ✅ `e16a655` | ✅ SF3 | ✅ SF3 |
| M8 | 主动回忆 | ✅ `1c5db1e` | ✅ SF4 | ✅ SF4 |
| M9 | 推送门面（横切） | ✅ | ✅ SF5 | ✅ SF5 |
| M10 | 抱抱卡分享 | ✅ `1c5db1e` | ✅ SF4 | ✅ SF4 |
| M11 | 内容运营（横切） | ✅ | ⏳ 规划中 | ⏳ 规划中 |

后端 v1 API 路径前缀：`/api/v1/...`（`/auth` 仍兼容 v0 旧路径）。

---

## 🧪 测试与质量门禁

```bash
# L0 格式化 + Lint
uv run ruff format .
uv run ruff check .
uv run mypy backend/app

# L1 单元测试
uv run pytest backend/tests/unit -q

# L2 Golden Set 回归（涉及 prompt 修改时必跑）
uv run pytest backend/tests/golden -q
# Eval Runner（schema 校验 + 4 种模式 pr/daily/release/schema）
python backend/eval/run_eval.py --mode pr

# L3 集成测试（依赖 docker compose 服务栈）
uv run pytest backend/tests/integration -q

# L4 BDD（pytest-bdd）
uv run pytest backend/tests/bdd -q

# L5 负载（locust）
locust -f backend/tests/load/locustfile_mvp.py --host=http://localhost:8000

# L6 覆盖率（目标 ≥ 60%）
uv run pytest --cov=backend/app --cov-report=term-missing --cov-fail-under=60
```

> 当前覆盖率约 **45%**（沿用 `142eab9f` worker 报告），Sprint 6 PR-Gate 回归一并补到 60%。

---

## 🔧 调试脚本

仓库根目录的 `scripts/` 提供 8 个调试脚本（落库于 `36dca24`）：

| 脚本 | 用途 |
|---|---|
| `check_bytes.py` | 检查文件编码（GBK / UTF-8） |
| `check_diag.py` | 诊断服务冒烟 |
| `check_imports.py` | 检查 `app.xxx` 是否可 import |
| `check_routes.py` | 列出所有 FastAPI 路由 |
| `fix-changelog.py` | CHANGELOG 格式修复 |
| `fix_ia_check2.py` | IA 自检脚本修复 |
| `fix_plan.py` | 方案数据修复 |
| `patch_checklist.py` | checklist 增量更新 |

---

## 🐛 已知遗留 WARN（不阻塞工程）

| ID | 描述 | 来源 |
|---|---|---|
| W1 | `share_service` 含禁用色 `#FF4D4F`（M10）；`recall_service` 硬编码错误码（M8）；`MinioStorage` `NotImplemented` | `86044e16` |
| W2 | 覆盖率约 45%（目标 60%）；`MinioStorage` `NotImplemented`；`test_main_lifespan.py` 偶发挂起；微信 `jscode2session` 全 mock；Recall summary 未接真实 LLM | `142eab9f` |
| W3 | 小程序 SF5 worker 自报 summary 待 review | `0f396185` |
| W4 | Flutter widget / golden tests 在 CI 跑通（本地沙盒无 SDK） | `559a5d7a` / `cb993b8d` |

均在 Sprint 6 PR-Gate 回归 + L0-L6 门禁一并修复。

---

## 🤝 贡献

⚠️ **本仓库不含 docs/ 目录**——PRD / SPEC / ADR / architecture / data-dictionary 含商业敏感信息，**仅本地保留**，**不公开**。

如果你想：
- 🐛 **提 Issue**：直接开 issue
- 🔀 **提 PR**：fork → feature 分支 → PR（详见 `.cursor/skills/pr-gate/SKILL.md`）
- 📖 **看设计文档**：请通过内部渠道获取 docs 仓库权限（私密）
- 💼 **商业合作 / 投资**：邮件 dev@selfwell.app

---

## 📜 License

[MIT](LICENSE) — 公开代码部分采用最宽松许可；商业文档与产品设计保留所有权利。

---

**品牌承诺**：我们不制造焦虑、不打分排名、不评判美丑、不横向对比。
**进度环仅自己可见**，无排行榜，无对比，无评判。