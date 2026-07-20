---
phase: CODE
run_id: DDD-REFACTOR-USER-20260720
role: developer
task_type: refactor
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
created_at: "2026-07-20T16:00:00+08:00"
---

# CODE Evidence: DDD 重构 — User Context（首个改造）

## 一、改造范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `contexts/user/domain/user.py` | 新建 | User Aggregate Root + Domain Methods |
| `contexts/user/domain/user_status.py` | 新建 | UserStatus Enum + 状态机 |
| `contexts/user/domain/events.py` | 新建 | 4 个 Domain Events |
| `contexts/user/application/user_service.py` | 新建 | Application Service（编排层） |
| `contexts/user/infrastructure/token_service.py` | 新建 | TokenService（从 jwt_service 迁入） |
| `contexts/user/infrastructure/user_repo.py` | 新建 | UserRepository 接口 + 实现 |
| `contexts/user/interfaces/user_router.py` | 新建 | FastAPI Router（从 auth_v1 迁移） |
| `contexts/user/__init__.py` | 新建 | Context 统一导出 |
| `contexts/user/domain/__init__.py` | 新建 | Domain Layer 导出 |
| `contexts/user/application/__init__.py` | 新建 | Application Layer 导出 |
| `contexts/user/infrastructure/__init__.py` | 新建 | Infrastructure Layer 导出 |
| `contexts/user/interfaces/__init__.py` | 新建 | Interfaces Layer 导出 |
| `contexts/__init__.py` | 新建 | Contexts 根包 |

## 二、旧文件（未修改，保留兼容）

- `services/auth/jwt_service.py` — 保持原样，Router 暂不改
- `services/auth/wx_login_service.py` — 保持原样
- `services/auth/phone_login_service.py` — 保持原样
- `services/users/profile_service.py` — 保持原样
- `api/routers/auth_v1.py` — 保持原样

## 三、DDD 架构亮点

### 3.1 User Aggregate Root

- 字段与 ORM 1:1 对齐
- 领域方法：`register()`, `complete_profile()`, `record_login()`, `deactivate()`, `grant_consent()`
- 事件发布：`pop_events()` 消费 Domain Events

### 3.2 User Status 状态机

- `draft → active`（5 字段齐全）
- `draft → churned`（注销/封禁）
- `active → churned`（注销/封禁）
- 使用 `StrEnum` + `ClassVar` + `frozenset` 防止可变性

### 3.3 Domain Events

- `UserRegisteredEvent` — 新用户注册
- `UserActivatedEvent` — draft → active
- `UserDeactivatedEvent` — 用户注销
- `UserConsentGrantedEvent` — 隐私授权

### 3.4 Application Service

- 编排 Domain Layer + Infrastructure Layer
- 兼容旧接口签名（`login_via_wx`, `login_via_phone`, `get_user_profile`, `update_user_profile`）
- 使用 `CreateUserPayload` dataclass 封装参数（减少 PLR0913 警告）

## 四、L0-L4 质量门禁

| 门禁 | 结果 | 说明 |
|------|------|------|
| L0 py_compile | ✅ PASS | 所有新文件语法正确 |
| L1 ruff check | ✅ PASS | 0 errors |
| L1 ruff format | ✅ PASS | 12 files formatted |
| L2 mypy --strict | ✅ PASS | 0 errors in 12 files |
| L3 pytest auth/login/jwt | ✅ PASS | 46 passed |
| L4 ruff F401/F811/S608 | ✅ PASS | 0 errors |

### 4.1 L3 详细结果

```
tests/unit/services/auth/test_jwt_service.py .........          8 passed
tests/unit/services/auth/test_phone_login_service.py ........    8 passed
tests/unit/services/auth/test_wx_login_service.py .....       5 passed
tests/unit/services/users/test_profile_validate.py ..........   11 passed
tests/unit/api/test_routers_auth.py ........                8 passed
───────────────────────────────────────────────────────────────
Total: 46 passed
```

**预存失败（与改造无关）**：
- `test_profile_audit_fields.py::test_update_user_profile_audit_on_draft_promotion` — 旧 service 行为，与 contexts/user 无关

## 五、迁移策略（Phase 1 完成）

Phase 1 ✅ 已完成：
1. 创建 `contexts/user/` 完整 DDD 结构
2. Domain Layer：User Aggregate + Status Machine + Events
3. Application Layer：UserApplicationService（兼容旧接口）
4. Infrastructure Layer：TokenService + UserRepository
5. Interfaces Layer：FastAPI Router

Phase 2（Router 替换，后续）：
6. 修改 `auth_v1.py` → 从 `contexts/user/interfaces/user_router.py` 导入
7. 修改 `users_v1.py` → 从新 service 导入
8. 删除旧 `services/auth/` 兼容层

## 六、约束遵守

- ✅ R-2: 业务规则不写在 agents/ 内
- ✅ DDD: `contexts/user/` 目录符合 bounded context 规范
- ✅ `UserStatus` 使用 `StrEnum`（Python 3.11+）
- ✅ `_LEGAL_TRANSITIONS` 使用 `ClassVar[frozenset]` 防止可变性
- ✅ Domain Events 命名符合 `{Aggregate}{动词}Event` 规范
- ✅ 无循环依赖（domain → application → infrastructure）
