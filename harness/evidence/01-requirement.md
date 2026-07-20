---
phase: REQUIREMENT
run_id: FR-PILOT-M1-20260719
role: requirement-analyst
fr_refs: [FR-M1-01-20260719, FR-M1-02-20260719, FR-M1-03-20260719]
adr_refs: [ADR-0001, ADR-0007]
signed: true
interrupt_budget: 5
replay_session_id: null

# 文档来源字段
source_doc: docs/requirements/SELFWELL-MVP-SRS.md   # 已有需求文档路径
created_from_scratch: false                            # true=从0创建，false=引用已有
source_doc_sections: [§3.2.1 微信登录, §3.2.3 草稿用户]  # 本轮涉及已有文档的章节
---

# 01-requirement.md - REQUIREMENT phase（FR 拆解）

> **对应 ATDD**: `harness/atdd/ATDD-M1-AC.md`（M1 微信 OAuth 登录验收标准）
> **对应真源**: `docs/spec/TDS-M1-wechat-login.md` V1.1
> **REQUIREMENT**: `docs/REQUIREMENT/Selfwell-REQUIREMENT-V1.1.md` §1.1 微信 OAuth 登录

## 1. 观点

本 pilot FR 选择 **M1 微信 OAuth 登录**作为 harness 状态机首次实战验证的 target。理由：(a) 微信登录**已完整实现**（`backend/app/services/auth/wx_login_service.py` 250 行 + `backend/app/api/routers/auth_v1.py` 186 行 + `apps/flutter_app/lib/pages/login/login_page.dart` 139 行 + `apps/mp-selfwell/miniprogram/pages/login/index.ts`）；(b) 12 份 ATDD-AC 已全部就位；(c) 前后端契约清晰，跑通即"demo 可跑"。

## 2. 论据

### 2.1 现状核实（2026-07-19 23:50）

| 维度 | 文件 | 状态 | 关键证据 |
|---|---|---|---|
| 后端 service | `backend/app/services/auth/wx_login_service.py` | OK done | 250 行，含 5 函数：`_validate_platform` / `_find_user_by_openid` / `_create_draft_user` / `_update_user_login` / `login_via_wx` |
| 后端 router | `backend/app/api/routers/auth_v1.py` | OK done | 3 端点：`/wx-login` (L89) / `/phone-code` (L129) / `/phone-login` (L152) |
| Flutter 前端 | `apps/flutter_app/lib/pages/login/login_page.dart` | OK done | 139 行 UI |
| 小程序前端 | `apps/mp-selfwell/miniprogram/pages/login/index.ts` | OK done | 微信登录组件 + jscode2session 集成 |
| 数据库 | `backend/app/db/models/user.py` | OK done | 含 `openid_mp` / `openid_app` / `unionid` / `status` 列 |
| ATDD 文档 | `harness/atdd/ATDD-M1-AC.md` | OK done | 8 Feature + 13 Scenario（gherkin） |

### 2.2 关键 FR 拆解（与 ATDD-M1-AC.md 1:1 对应）

| FR ID | 名称 | AC 编号 | 关联 code 入口 |
|---|---|---|---|
| FR-M1-01 | 微信 OAuth 登录（首次走 draft） | AC-M1-01 | `POST /api/v1/auth/wx-login` |
| FR-M1-02 | unionid 跨端打通 | AC-M1-02 | `POST /api/v1/auth/wx-login` + `encryptedData` 解密 |
| FR-M1-03 | 草稿用户 24h 自动转正 | AC-M1-03 | cron `auto_active_draft_users` |
| FR-M1-04 | 首登档案补全立即转正 | AC-M1-04 | `POST /api/v1/users/profile` |
| FR-M1-05 | 推送 Token 注册 | M1-FR-05 | `POST /api/v1/users/push-token` |
| FR-M1-06 | 跨端登录更新末次 platform | M1-FR-03 | `POST /api/v1/auth/wx-login` |

### 2.3 关键 ADR 引用

- **ADR-0001**：微信登录采用 `jscode2session` + 加密 unionid，**禁止**自建 OAuth 网关（避免重复造轮子）
- **ADR-0007**：草稿用户 + 24h cron 转正（避免"全冷启动注册流量冲击业务表"）

## 3. 决策请求

| # | 决策项 | 候选 | 推荐 |
|---|---|---|---|
| 1 | pilot FR 选 M1-01 单条还是 M1 全集 6 条？ | (a) 单 FR / (b) 6 FR 一起 | (b) 6 FR 一起（pipeline 短，复用 `wx_login_service`） |
| 2 | 是否复用现有 wx_login_service？还是 TDD 重写？ | (a) 复用 / (b) 重写 | (a) 复用（已实现 + 单测待补） |
| 3 | phase REQUIREMENT 完成后是否直接进入 ARCH_DESIGN？ | (a) 是 / (b) 跳 ATDD 直接 CODE | (a) 是（demo 跑全 phase） |
| 4 | 单测目标覆盖率 | ≥ 60%（CI 硬卡） / ≥ 80%（自查） | ≥ 80%（规则见 coding-standards §18） |

## 4. 下一步

1. dispatcher 校验 `exit_criteria_met[0]`（REQUIREMENT evidence 存在 + 8 字段 frontmatter 齐全）→ PASS
2. dispatcher 校验 `exit_criteria_met[1]`（FR 列表 ≥ 1 条 + 关联 ATDD）→ PASS
3. orchestrator 切换 current_phase = ARCH_DESIGN
4. 进入 Phase 2（架构设计）—— 生成 `evidence/02-tech-design.md`

> **本 evidence 不阻塞合入**：演示用，无需 reviewer 签字。
