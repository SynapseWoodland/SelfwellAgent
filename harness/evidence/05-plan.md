---
phase: PLAN
run_id: DDD-REFACTOR-USER-20260720
role: plan-generator
task_type: refactor
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
created_at: "2026-07-20T15:51:00+08:00"
---

# PLAN: DDD 重构 — User Context（首个改造）

## 一、重构目标

**范围**：仅改造 `services/auth/` + `services/users/profile_service.py` → DDD `contexts/user/` 结构。
**原则**：`其他服务代码不动`，最小化风险。

---

## 二、当前代码分析

### 2.1 现有文件清单（仅改这些）

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/auth/jwt_service.py` | 144 | JWT 签发/校验/失效 |
| `services/auth/wx_login_service.py` | 251 | 微信登录（code2session → upsert user → JWT） |
| `services/auth/phone_login_service.py` | 216 | 手机号验证码登录 |
| `services/users/profile_service.py` | 232 | 用户档案 get/update/validate |
| `api/routers/auth_v1.py` | 187 | Auth API 路由 |
| `api/routers/users_v1.py` | — | User API 路由（需适配） |

### 2.2 核心不变量识别

| 不变量 | 位置 |
|-------|------|
| user_id 必须是合法 UUID 字符串（≥16字符） | `jwt_service._validate_user_id` |
| platform 必须是 `wx_mp/ios/android/harmony` | `wx_login_service._validate_platform` |
| 手机号 11 位数字 | `phone_login_service._validate_phone` |
| 验证码 4-6 位数字 | `phone_login_service._validate_code` |
| 5 字段齐了 `draft → active` | `profile_service._has_minimum_profile` |

### 2.3 跨服务调用依赖

```
Router (auth_v1.py)
  ├── wx_login_service.login_via_wx()
  │     └── jwt_service.issue_token()
  ├── phone_login_service.request_sms_code()
  └── phone_login_service.login_via_phone()
        └── jwt_service.issue_token()

Router (users_v1.py)
  └── profile_service.{get,update}_user_profile()
```

---

## 三、User Context DDD 设计

### 3.1 Bounded Context 定义

- **Context**: User
- **通用语言**: "用户通过微信/手机号注册登录，完善档案后成为正式用户"
- **Aggregate Root**: `User`（保持与现有 ORM 一致）
- **核心不变式**:
  1. `unionid` 全局唯一
  2. `status` 状态机: `draft` → `active` → `churned`（仅此路径）
  3. 5 字段齐全时 `draft → active`

### 3.2 Domain Events

| Event | 触发时机 | Consumer |
|-------|---------|----------|
| `UserRegisteredEvent` | 新用户创建（微信/手机号） | Notification |
| `UserActivatedEvent` | 5 字段齐全，draft → active | Plan, Community |
| `UserDeactivatedEvent` | 用户注销 | All Contexts |
| `UserConsentGrantedEvent` | 隐私授权 | All Contexts |

### 3.3 目录结构（新建）

```
backend/app/contexts/user/
├── domain/
│   ├── __init__.py
│   ├── user.py          # User Aggregate Root
│   ├── user_status.py   # UserStatus Enum + 状态机
│   └── events.py        # Domain Events（UserRegisteredEvent 等）
├── application/
│   ├── __init__.py
│   ├── user_service.py  # Application Service（登录/档案/Token 编排）
│   ├── commands.py      # Command DTOs（CreateUserCommand 等）
│   └── queries.py        # Query DTOs（GetUserProfileQuery 等）
├── infrastructure/
│   ├── __init__.py
│   ├── user_repo.py     # Repository 实现（SQLAlchemy）
│   └── token_service.py # JWT Token Service（从 jwt_service 迁入）
└── interfaces/
    ├── __init__.py
    └── user_router.py   # FastAPI Router（从 auth_v1/users_v1 迁移）

# 旧文件标记 DEPRECATED（不改内容，仅 __all__ 提示迁移方向）
backend/app/services/auth/jwt_service.py    → DEPRECATED
backend/app/services/auth/wx_login_service.py → DEPRECATED
backend/app/services/auth/phone_login_service.py → DEPRECATED
backend/app/services/users/profile_service.py  → DEPRECATED
```

### 3.4 迁移策略（Phase-by-Phase）

**Phase 1（本期）**: 新建 `contexts/user/` + 兼容层

1. 创建 `contexts/user/` 目录结构
2. 在 `contexts/user/domain/user.py` 定义 User Aggregate（引用现有 ORM）
3. 在 `contexts/user/application/user_service.py` 实现核心方法
4. 保留旧 `services/` 作为兼容层（加 DEPRECATED 注释）
5. Router 层先**不改**，通过 `services/` 路由到新 service

**Phase 2（后续）**: 替换 Router 调用

6. 修改 `auth_v1.py` / `users_v1.py` 指向新 `contexts/user/interfaces/user_router.py`
7. 删除 `services/` 旧文件

---

## 四、实施计划

### 4.1 代码改造（Phase 1，本期）

| 步骤 | 任务 | 依赖 | 估算 |
|------|------|------|------|
| 1 | 创建 `contexts/user/` 目录骨架 | — | 10min |
| 2 | 定义 `domain/user.py`（User Aggregate + 不变量校验） | 现有 ORM | 20min |
| 3 | 定义 `domain/events.py`（4 个 Domain Event） | Step 2 | 15min |
| 4 | 实现 `infrastructure/user_repo.py`（引用现有 ORM 查询） | Step 2 | 20min |
| 5 | 实现 `infrastructure/token_service.py`（从 jwt_service 迁入） | Step 2 | 15min |
| 6 | 实现 `application/user_service.py`（登录/档案服务） | Step 4,5 | 30min |
| 7 | 兼容层：旧 `services/` 加 DEPRECATED 注释 | Step 6 | 5min |
| 8 | Router 暂时不动，验证新旧 service 返回值一致 | Step 1-7 | 20min |

**总估算**: ~135 分钟（2.25 小时）

### 4.2 质量门禁

| 门禁 | 命令 |
|------|------|
| L0 | `python -m py_compile backend/app/contexts/user/**/*.py` |
| L1 | `uv run ruff check backend/app/contexts/user/ --fix && uv run ruff format --check backend/app/contexts/user/` |
| L2 | `uv run mypy --strict backend/app/contexts/user/` |
| L3 | `uv run pytest tests/unit -x -q` |
| L4 | `uv run ruff check backend/app/contexts/user/ --select=F401,F811,S608,S307,SEC,B,B003` |

---

## 五、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 迁移期间 API 不兼容 | 高 | 旧 services 保留，Router 分阶段替换 |
| ORM 模型与 Domain 耦合 | 中 | Domain 层引用 ORM，Infrastructure 负责映射 |
| 循环依赖 | 低 | 严格按 `domain → application → infrastructure` 依赖方向 |

---

## 六、回滚计划

若 Phase 1 失败，保留 `services/` 旧代码不做修改，直接回退。
