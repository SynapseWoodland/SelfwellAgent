# SelfwellAgent 多 Agent 协作编排

> 本文件定义 Cursor AI Agent 的角色分工、触发条件和调用规范。
> 所有 Agent 均以本文件为调度依据，遵循 `.cursorrules` 入口规则的最高优先级禁止项。

---

## Agent 角色矩阵

| 角色 | 职责范围 | 触发关键字 / 场景 |
|------|----------|-------------------|
| **Backend Agent** | Python / FastAPI / LangGraph / SQLAlchemy 后端全栈 | `backend/`、`agents/`、`rules/`、`pyproject.toml`、`.py` 文件 |
| **Frontend Agent** | Flutter / 微信小程序 / TypeScript 前端全栈 | `apps/`、`components/`、`pages/`、`.tsx`、`.dart`、`.ts` 文件 |
| **QA Agent** | 测试设计与执行、L0-L6 质量门禁、Golden Set 维护 | `tests/`、`pytest`、`golden_set/`、`coverage`、`--cov` |
| **DevOps Agent** | Docker / CI/CD / 环境配置 / 数据库迁移 | `docker-compose.yaml`、`.env`、`.github/`、`alembic/`、`db/init/` |
| **Security Agent** | 代码安全审计、敏感信息检测、依赖漏洞扫描 | `bandit`、安全扫描、权限审计、密钥泄露 |

---

## Agent 技能依赖表

```
Backend Agent
  ├── 必须读: .cursor/skills/coding-standards/SKILL.md
  ├── 必须读: .cursor/skills/coding-standards/RULES.md
  ├── 必须读: .cursor/skills/coding-standards/GATES.md
  ├── 必须读: .cursor/skills/coding-standards/PATTERNS.md
  ├── 必须读: .cursor/skills/coding-standards/EXAMPLES.md
  └── 可选读: .cursor/skills/golden-set/SKILL.md（涉及 Prompt 修改时）

Frontend Agent
  ├── 必须读: .cursor/skills/frontend-standards/SKILL.md
  └── 可选读: .cursor/skills/sdd-tdd/SKILL.md（涉及设计方案时）

QA Agent
  ├── 必须读: .cursor/skills/coding-standards/GATES.md
  ├── 必须读: .cursor/skills/golden-set/SKILL.md
  └── 可选读: coding-standards/EXAMPLES.md

DevOps Agent
  ├── 必须读: README.md（docker compose 部分）
  └── 必须读: .cursor/skills/pr-gate/SKILL.md（提交流前）

Security Agent
  └── 必须读: .cursor/skills/coding-standards/RULES.md（安全规则部分）
```

---

## Agent 触发规则

### 1. Backend Agent

**自动触发条件**（满足任一即激活）：
- 用户打开 / 编辑 `backend/**/*.py` 文件
- 用户消息包含 `backend`、`fastapi`、`langgraph`、`sqlalchemy`、`agent`、`node`、`service`
- 用户请求涉及 `agents/`、`rules/`、`prompts/` 目录

**工作流程**：
1. 读取 `.cursor/skills/coding-standards/SKILL.md`
2. 读取 `.cursor/skills/coding-standards/GATES.md`
3. 编写 / 审查 / 重构代码
4. 提交前执行 L0-L6 质量门禁（见 GATES.md）
5. 如涉及 Prompt 修改，启动 Golden Set 回归（读 golden-set SKILL.md）

---

### 2. Frontend Agent

**自动触发条件**（满足任一即激活）：
- 用户打开 / 编辑 `apps/flutter_app/` 或 `apps/mp-selfwell/` 下的文件
- 用户消息包含 `flutter`、`小程序`、`miniprogram`、`widget`、`page`、`dart`、`typescript`
- 用户请求涉及 `components/`、`pages/`、`utils/` 目录

**工作流程**：
1. 读取 `.cursor/skills/frontend-standards/SKILL.md`
2. 编写 / 审查 / 重构 Flutter / 微信小程序代码
3. 遵循组件规范、状态管理规范、国际化规范
4. 提交前执行 lint 检查

---

### 3. QA Agent

**自动触发条件**（满足任一即激活）：
- 用户打开 / 编辑 `backend/tests/` 目录
- 用户消息包含 `test`、`pytest`、`coverage`、`golden`、`eval`、`regression`
- 用户请求涉及 `golden_set_v*.yaml`、`run_eval.py`、`conftest.py`

**工作流程**：
1. 读取 `.cursor/skills/coding-standards/GATES.md`
2. 读取 `.cursor/skills/golden-set/SKILL.md`
3. 设计 / 执行测试用例
4. 运行覆盖率检查（目标 ≥ 60%）
5. 运行 Golden Set 回归（如涉及 Prompt 修改）
6. 输出测试报告和质量门禁结果

---

### 4. DevOps Agent

**自动触发条件**（满足任一即激活）：
- 用户打开 / 编辑 `docker-compose.yaml`、`.env`、`.github/workflows/`、`db/init/`、`alembic/`
- 用户消息包含 `docker`、`ci`、`deploy`、`migration`、`db`、`redis`、`minio`
- 用户请求涉及环境配置、容器编排、数据库迁移

**工作流程**：
1. 读取 README.md 的 docker compose 部分
2. 执行 `docker compose` 命令操作
3. 执行 Alembic 迁移（`alembic upgrade head`）
4. 遵循 `.cursor/skills/pr-gate/SKILL.md` 提交流规范

---

### 5. Security Agent

**自动触发条件**（满足任一即激活）：
- 用户打开 / 编辑 `.env`、密钥相关文件
- 用户消息包含 `security`、`安全`、`scan`、`vulnerability`、`secret`、`key`
- 用户请求涉及权限审计、依赖漏洞检测

**工作流程**：
1. 读取 `.cursor/skills/coding-standards/RULES.md`
2. 运行 `bandit -r backend/app` 安全扫描
3. 检查敏感信息泄露（API Key、JWT Secret、密码）
4. 审查依赖漏洞（`pip audit` 或 `safety check`）
5. 输出安全审计报告

---

## Agent 间协作规范

### 跨 Agent 任务

当任务涉及多个 Agent 职责范围时，**按以下顺序协作**：

1. **Backend → Frontend**：后端 API 契约确定后，前端 Agent 才能实现对接
2. **QA → Backend**：测试用例设计完成后，Backend Agent 按 TDD 驱动实现
3. **DevOps → Backend**：环境就绪后，Backend Agent 才启动开发
4. **Security → All**：安全审计结果作为所有 Agent 的前置约束

### Agent 冲突解决

- **规范冲突**：以 `.cursor/skills/coding-standards/SKILL.md` 为唯一真源
- **技术选型冲突**：查阅 `docs/adr/` 目录的 ADR 决策记录
- **测试与实现冲突**：以测试用例（QA Agent 输出）为准，Backend Agent 修复实现

---

## Agent 质量门禁集成

| Agent | 门禁要求 |
|-------|----------|
| Backend Agent | L0: ruff format + ruff check + mypy<br>L1: pytest unit<br>L2: Golden Set 回归（如涉及 Prompt）<br>L3: pytest integration<br>L6: coverage ≥ 60% |
| Frontend Agent | Flutter: flutter analyze + flutter test<br>小程序: npm run lint |
| QA Agent | 全量 L0-L6 门禁通过 |
| DevOps Agent | docker compose ps 健康检查通过 |
| Security Agent | bandit 无 S 高危 + 无敏感信息泄露 |

---

## 禁止事项（所有 Agent 通用）

- 禁止在 `agents/` 目录内编写业务规则（必须放 `rules/`）
- 禁止不在 `pyproject.toml` 声明依赖
- 禁止提交前未跑通 L0-L6 质量门禁
- 禁止修改 Prompt 但未跑对应版本 Golden Set 回归
- 禁止硬编码密钥或敏感信息
- 禁止在非 docs/ 目录存放商业敏感文档

---

## 文件归属速查

| 文件 / 目录 | 主要负责 Agent |
|-------------|---------------|
| `backend/app/` | Backend Agent |
| `backend/tests/` | QA Agent + Backend Agent |
| `backend/eval/` | QA Agent |
| `apps/flutter_app/` | Frontend Agent |
| `apps/mp-selfwell/` | Frontend Agent |
| `packages/` | Frontend Agent |
| `db/init/` | DevOps Agent |
| `docker-compose.yaml` | DevOps Agent |
| `.env` / `.env.example` | DevOps Agent + Security Agent |
| `.github/workflows/` | DevOps Agent |
| `docs/` | 全部 Agent（按需引用） |
| `.cursor/rules/` | 全部 Agent（只读真源） |
| `.cursor/skills/` | 全部 Agent（只读真源） |
