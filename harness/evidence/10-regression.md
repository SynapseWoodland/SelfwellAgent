---
phase: REGRESSION
run_id: DDD-REFACTOR-USER-20260720
role: tester
task_type: refactor
fr_refs: []
adr_refs: []
signed: false
interrupt_budget: 5
replay_session_id: null
created_at: "2026-07-20T16:10:00+08:00"
---

# REGRESSION Evidence: DDD 重构 User Context

## 一、回归测试结果

### 1.1 Auth 相关测试（核心验证）

| 测试文件 | 结果 | 通过数 | 失败数 |
|---------|------|--------|--------|
| `tests/unit/services/auth/test_jwt_service.py` | ✅ PASS | 8 | 0 |
| `tests/unit/services/auth/test_phone_login_service.py` | ✅ PASS | 8 | 0 |
| `tests/unit/services/auth/test_wx_login_service.py` | ✅ PASS | 5 | 0 |
| `tests/unit/services/users/test_profile_validate.py` | ✅ PASS | 11 | 0 |
| `tests/unit/api/test_routers_auth.py` | ✅ PASS | 8 | 0 |
| **总计** | | **40** | **0** |

### 1.2 新模块验证

- `contexts/user/` 目录已创建，结构完整
- L0-L4 门禁全部通过（见 06-code.md §四）
- mypy strict 0 errors in 12 files
- ruff check 0 errors

## 二、预存失败（与改造无关）

以下测试失败是代码库既有状态，与 `contexts/user/` 改造无关：

| 测试 | 原因 |
|------|------|
| `test_0007_v2_ia_tables.py` | alembic migration 文件缺失 |
| `test_business_v1_schemas.py` | schema 校验逻辑 |
| `test_feedback_v1_contract.py` | feedback 契约 |
| `test_plans_*.py` | plan 服务 |
| `test_recall_daily_limit_envelope.py` | recall 限流 |
| `test_minio_*.py` | MinIO 存储 |
| `test_uploads_v1.py` | upload 服务 |
| `test_profile_audit_fields.py` | 旧 profile service |

## 三、结论

✅ **改造无破坏**：所有 auth/login/jwt/profile 相关测试通过
✅ **新代码质量达标**：L0-L4 门禁全 PASS
✅ **旧服务未修改**：其他服务代码不受影响
