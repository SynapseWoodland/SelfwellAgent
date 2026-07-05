# Selfwell 自愈 · AI 智能健康陪伴

> **V1.3 MVP（2026-07-05）** · iOS APP（Flutter）+ 微信小程序 · 1 人 + AI 加速

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
| **SQLAlchemy 2.0 + asyncpg** | PostgreSQL 15 ORM |
| **Pydantic 2** | 配置 / 数据校验 |
| **LangChain / LangGraph** | Agent 编排 + 4 级 LLM 降级 |
| **Redis** | 缓存 / 限流 |
| **MinIO** | 对象存储（照片 / 海报） |
| **Loguru** | 结构化日志 |

### 客户端

| 平台 | 技术 |
|---|---|
| **iOS APP** | Flutter 3.22（V1.3 优先） |
| **微信小程序** | 微信原生 + TypeScript |

---

## 🚀 快速启动

### 后端

```bash
# 1. 安装 Python 3.12 + uv
pip install uv

# 2. 克隆仓库
git clone https://github.com/<yourname>/selfwell-agent.git
cd selfwell-agent

# 3. 安装依赖
uv sync --all-extras

# 4. 启动开发服务
uv run uvicorn backend.app.main:app --reload --port 8000
```

### 微信小程序

```bash
cd apps/mp-selfwell
# 用微信开发者工具打开本目录
# 替换 project.config.json 的 appid 为你的 AppID
```

### Flutter APP

```bash
cd apps/flutter_app
flutter pub get
flutter run -d ios
```

---

## 📂 项目结构

```
selfwell-agent/
├── backend/               # Python 后端（FastAPI）
│   ├── app/
│   │   ├── api/v1/        # REST 路由
│   │   ├── services/      # 业务服务层
│   │   └── conf/          # 统一配置
│   ├── tests/             # 测试（Golden Set / Eval Runner / pytest）
│   └── eval/              # Eval Runner + golden_set_v1.yaml
├── apps/                  # 客户端脚手架（monorepo: apps/ + packages/）
│   ├── flutter_app/       # iOS Flutter APP（MVP）
│   └── mp-selfwell/       # 微信小程序
├── packages/              # 跨端共享（design-tokens / lint-rules / api-types）
├── .github/workflows/     # CI 流水线
│   └── backend-ci.yml
├── pyproject.toml         # 依赖 + Lint 配置
└── README.md              # 你正在读的
```

---

## 📋 业务模块（M1-M11）

| ID | 模块 | 状态 |
|---|---|---|
| M1 | 极简登录 / 用户档案 | ✅ Phase 0 |
| M2 | AI 多模态联合诊断 | ✅ Phase 0 |
| M3 | 21 天方案生成 | ✅ Phase 0 |
| M4 | 每日打卡闭环 | ✅ Phase 0 |
| M5 | 智能管家对话主页 | ✅ Phase 0 |
| M6 | 蜕变广场 | ✅ Phase 0 |
| M7a | 心情日记 | ✅ Phase 0 |
| M7b | 多部位反馈 | ✅ Phase 0 |
| M8 | 主动回忆 | ✅ Phase 0 |
| M9 | 推送门面（横切） | ✅ Phase 0 |
| M10 | 抱抱卡分享 | ✅ Phase 0 |
| M11 | 内容运营（横切） | ✅ Phase 0 |

---

## 🤝 贡献

⚠️ **本仓库不含 docs/ 目录**——PRD / SPEC / ADR / architecture / data-dictionary 含商业敏感信息，**仅本地保留**，**不公开**。

如果你想：
- 🐛 **提 Issue**：直接开 issue
- 🔀 **提 PR**：fork → feature 分支 → PR
- 📖 **看设计文档**：请通过内部渠道获取 docs 仓库权限（私密）
- 💼 **商业合作 / 投资**：邮件 dev@selfwell.app

---

## 📜 License

[MIT](LICENSE) — 公开代码部分采用最宽松许可；商业文档与产品设计保留所有权利。

---

**品牌承诺**：我们不制造焦虑、不打分排名、不评判美丑、不横向对比。
**进度环仅自己可见**，无排行榜，无对比，无评判。
