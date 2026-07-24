# P1 待办清单 — 后台能力 + RBAC 权限体系 + 合规功能

> **版本**: V0.3
> **日期**: 2026-07-22
> **作者**: Selfwell Agent
> **状态**: Draft（待产品/运营评审）
> **触发源**: 
> 1. 在梳理 ATDD-Compliance / TDS-M14 时发现：部分功能**有业务真源和验收标准**，但**前端设计稿无对应页面 + 交互**
> 2. 合规功能对比前端设计稿与后端文档，发现 MVP/P1 分工边界

---

## 一、问题描述

### 1.1 已识别的"无前端页面"功能

| # | 功能 | 业务真源 | 前端设计稿 | 性质 |
|---|------|---------|----------|------|
| 1 | 运营人工审核后台（社区内容三段式审核） | ATDD-Compliance §一 / TDS-M14 §2.4 | 无 | 运营侧 Web |
| 2 | 活动发布（运营/产品驱动） | ATDD-Community §? / TDS-M6 §? | 无 | 运营侧 Web |
| 3 | 敏感词库管理（sensitive_words 表 CRUD + 版本管理） | ATDD-Compliance §七 / TDS-M14 §5.2 | 无 | 运营侧 Web |
| 4 | 危机词表季度审查（关键词覆盖率自检 + 词条评审 + 归档） | ATDD-Compliance §三 / TDS-M14 §6.2 | 无 | 运营侧 Web |
| 5 | 合规率每日报告（拦截次数 / 违规率 / 危机升级次数） | ATDD-Compliance §九 | 无 | 运营侧报表 |
| 6 | safety_audit_logs 查询 / 导出 | TDS-M14 §5.1 | 无 | 运营侧查询 |
| 7 | RBAC 权限体系（4 类角色：用户 / 运营 / 审核员 / 管理员） | **缺失**（需新建 ADR） | 无 | 横切关注点 |

### 1.2 合规功能前端已有 vs 前端缺失

| # | 功能 | 业务真源 | 前端设计稿 | MVP/P1 |
|---|------|---------|----------|--------|
| **已有（MVP 实现）** |
| 7.1 | L-Crisis 危机响应卡 | ATDD-Compliance §三 / TDS-M14 §4.2 | 节点 30 | **MVP** |
| 7.2 | 隐私协议前置弹窗 | ATDD-Auth §零 | 节点 31 | **MVP** |
| 7.3 | 隐私政策页面 | PRD §1.0 | 节点 20 | **MVP** |
| 7.4 | 基线问候模板池（4 档） | PRD §1.4 | 节点 0 | **MVP** |
| 7.5 | 打卡完成合规文案（无量化） | PRD §3.2 | 节点 11 | **MVP** |
| 7.6 | 打卡完成无效果承诺 | PRD §1.8 | 节点 11 | **MVP** |
| **缺失（P1 实现）** |
| 7.7 | L-Serious 严重情绪响应卡 | ATDD-Compliance §三 / TDS-M14 §4.1 | 无 | **P1** |
| 7.8 | L-Medical 医疗急迫响应卡 | ATDD-Compliance §三 / TDS-M14 §4.1 | 无 | **P1** |
| 7.9 | 社区发布前的合规提示弹窗 | ATDD-Compliance §一 L4 | 无 | **P1** |
| 7.10 | 智能管家对话 L-Crisis 触发时的弹窗 | ATDD-Compliance §三 | 无（复用节点 30？） | **P1** |
| 7.11 | 社区内容发布合规引导页 | ATDD-Compliance §一 | 无 | **P1** |
| 7.12 | 心情日记合规提示 | ATDD-Compliance §二 C-1~C-6 | 无 | **P1** |

### 1.3 为什么部分合规功能挪到 P1

- **L-Crisis 已原型化**：节点 30 已实现，MVP 阶段直接使用
- **L-Serious/L-Medical 无原型**：需要新建设计稿（建议复用 L-Crisis 视觉风格）
- **MVP 1 人运营**：可借助现有流程跑通最小审核（合规是后端能力，前端 MVP 先跑通主流程）
- **P1 才需要独立运营后台**：当 DAU > 1000 或运营 > 1 人时，必须有专门的 Web 后台

---

## 二、P1 待办清单（P1 Backlog）

### 2.1 后台能力清单

| ID | 模块 | 优先级 | 依赖 | 预计工作量 | 验收来源 |
|----|------|:----:|------|:----:|---------|
| **P1-BE-01** | RBAC 权限体系（用户/运营/审核员/管理员） | P0 | - | 2 周 | §三 |
| **P1-BE-02** | 运营后台登录 + 工作台首页 | P0 | P1-BE-01 | 1 周 | §五.1 |
| **P1-BE-03** | 社区内容人工审核队列（通过/拒绝 + 评论） | P0 | P1-BE-02 | 2 周 | ATDD-Compliance §一 L4 / TDS-M14 §2.4 |
| **P1-BE-04** | 活动发布工作台（创建/编辑/上下架活动） | P1 | P1-BE-02 | 1.5 周 | PRD §? |
| **P1-BE-05** | 敏感词库管理（CRUD + 版本号 + 冷却期） | P0 | P1-BE-02 | 1 周 | ATDD-Compliance §七 / TDS-M14 §5.2 |
| **P1-BE-06** | 危机词表季度审查（覆盖率自检 + 词条评审） | P1 | P1-BE-05 | 1 周 | ATDD-Compliance §三 |
| **P1-BE-07** | safety_audit_logs 查询 + 导出（CSV/Excel） | P1 | - | 0.5 周 | TDS-M14 §5.1 |
| **P1-BE-08** | 合规率每日报告（拦截/违规率/危机升级） | P1 | P1-BE-07 | 0.5 周 | ATDD-Compliance §九 |
| **P1-BE-09** | 合规引擎 L1 词库 + BloomFilter 实现 | P0 | - | 1 周 | ATDD-Compliance §一 L1 |
| **P1-BE-10** | 合规引擎 L3 输出网关 + BloomFilter 实现 | P0 | P1-BE-09 | 1 周 | ATDD-Compliance §一 L3 |
| **P1-BE-11** | L-Crisis 同步阻塞拦截（<50ms） | P0 | P1-BE-09 | 0.5 周 | ATDD-Compliance §三 |

### 2.2 前端能力清单

| ID | 模块 | 优先级 | 依赖 | 预计工作量 | 验收来源 |
|----|------|:----:|------|:----:|---------|
| **P1-FE-01** | L-Crisis 危机响应卡组件化（适配生产 + 跳转） | P0 | - | 0.5 周 | 节点 30 |
| **P1-FE-02** | L-Serious 严重情绪响应卡（复用节点 30 风格） | P1 | P1-BE-11 | 0.5 周 | ATDD-Compliance §三 |
| **P1-FE-03** | L-Medical 医疗急迫响应卡（复用节点 30 风格） | P1 | P1-BE-11 | 0.5 周 | ATDD-Compliance §三 |
| **P1-FE-04** | 社区发布前合规提示弹窗 | P1 | P1-BE-10 | 0.5 周 | ATDD-Compliance §一 |
| **P1-FE-05** | 心情日记合规提示 | P1 | P1-BE-10 | 0.5 周 | ATDD-Compliance §二 |

### 2.3 MVP 合规实现清单（当前 sprint 必做）

| ID | 模块 | 前端设计稿 | 验收来源 |
|----|------|-----------|---------|
| **MVP-FE-01** | L-Crisis 危机响应卡（已有原型） | 节点 30 | ATDD-Compliance §三 L-Crisis |
| **MVP-FE-02** | 隐私协议前置弹窗 | 节点 31 | ATDD-Auth §零 |
| **MVP-FE-03** | 隐私政策页面 | 节点 20 | PRD §1.0 |
| **MVP-FE-04** | 基线问候模板池（4 档） | 节点 0 | PRD §1.4 |
| **MVP-FE-05** | 打卡完成合规文案（无量化） | 节点 11 | PRD §3.2 |
| **MVP-FE-06** | 打卡完成无效果承诺 | 节点 11 | PRD §1.8 |

### 2.4 依赖图

```
P1-BE-09 (L1 合规引擎)
    |
    ├─→ P1-BE-10 (L3 输出网关)
    |       |
    |       ├─→ P1-FE-04 (社区合规提示)
    |       └─→ P1-FE-05 (心情日记合规)
    |
    └─→ P1-BE-11 (L-Crisis 同步拦截)
            |
            ├─→ P1-FE-02 (L-Serious 响应卡)
            └─→ P1-FE-03 (L-Medical 响应卡)

P1-BE-01 (RBAC)
    |
    ├─→ P1-BE-02 (运营工作台)
    |       |
    |       ├─→ P1-BE-03 (审核队列)      ─┐
    |       ├─→ P1-BE-04 (活动发布)      ─┤ 并行
    |       ├─→ P1-BE-05 (敏感词管理)    ─┘
    |       |       |
    |       |       └─→ P1-BE-06 (词表审查)
    |       └─→ P1-BE-08 (合规报告)
    |
    ├─→ P1-BE-07 (审计日志查询)

P1-FE-01 (危机响应卡) — 与 BE 并行（已有原型）
```

---

## 三、RBAC 权限体系（新建 ADR 占位）

> **本节内容未来将抽离为 `docs/architecture/adr/0020-rbac-role-based-access-control.md`**
> **本节为 P1 实施时的设计草案**

### 3.1 角色定义（4 类）

| 角色 | 编码 | 业务职责 | 典型场景 |
|------|------|---------|---------|
| **用户** | `user` | 使用小程序全部功能 | 查看报告/打卡/对话/反馈 |
| **运营** | `operator` | 内容运营 + 活动运营 | 审核社区内容、发布活动、查报告 |
| **审核员** | `reviewer` | 专注社区审核 + 危机干预 | 审核社区内容、处理危机升级 |
| **管理员** | `admin` | 系统配置 + 权限管理 | 词库管理、用户管理、角色分配 |

### 3.2 权限矩阵（粗粒度）

| 资源 / 动作 | user | operator | reviewer | admin |
|------------|:----:|:--------:|:--------:|:-----:|
| 小程序全部功能 | 是 | 是 | 是 | 是 |
| 运营后台登录 | 否 | 是 | 是 | 是 |
| 查看社区审核队列 | 否 | 是 | 是 | 是 |
| 审核社区内容（通过/拒绝） | 否 | 是 | 是 | 是 |
| 处理 L-Crisis 危机升级 | 否 | 仅引导 | 是 | 是 |
| 发布/编辑活动 | 否 | 是 | 否 | 是 |
| 敏感词库 CRUD | 否 | 否 | 否 | 是 |
| 危机词表审查 | 否 | 否 | 是 | 是 |
| 审计日志查询 | 否 | 仅自己 | 仅自己 | 全员 |
| 审计日志导出 | 否 | 否 | 否 | 是 |
| 用户角色分配 | 否 | 否 | 否 | 是 |
| 合规率报告查看 | 否 | 是 | 是 | 是 |

### 3.3 实现要点

#### 3.3.1 后端（FastAPI）

- **JWT Token 中携带 role**：在 JWT payload 增加 `role: "operator" | "reviewer" | "admin" | "user"`
- **依赖注入式守卫**：`require_role("admin")` / `require_any_role("operator", "admin")`
- **路径前缀隔离**：`/api/v1/admin/*` 强制要求非 user 角色；`/api/v1/user/*` 强制 user 角色
- **资源级权限**：在 Service 层校验（如 `audit_log.export(user_id, role)`，admin 可全员，其他角色仅自己）

```python
# backend/app/auth/guards.py（草案）
from fastapi import Depends, HTTPException
from app.auth.jwt import get_current_user

def require_role(*allowed_roles: str):
    """依赖注入守卫：仅允许指定角色访问"""
    def _check(user = Depends(get_current_user)) -> None:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail={"code": "E_AUTH_FORBIDDEN", "message_zh": "无权限访问"},
            )
    return _check

# 使用示例
@router.post("/api/v1/admin/sensitive-words", dependencies=[Depends(require_role("admin"))])
async def create_sensitive_word(...):
    ...
```

#### 3.3.2 前端（运营后台 Web）

- **统一布局**：`/admin/*` 路径下显示运营后台壳（顶栏 + 侧边菜单），登录态失效跳登录
- **菜单按角色过滤**：菜单配置按 role 过滤，未授权菜单不渲染
- **按钮级控制**：前端不依赖前端隐藏来保证安全，后端 API 必须再校验一次

### 3.4 用户-角色映射

| 来源 | 角色映射规则 |
|------|------------|
| 微信小程序首次登录 | 默认 `user` |
| 运营团队成员 | 飞书后台录入 → 推送 OpenAPI → 后台写入 `admin_users` 表 |
| 角色升级（如 user → reviewer） | admin 在后台手动分配 |
| 角色降级 / 注销 | admin 操作，软删除（保留 90 天审计） |

### 3.5 数据模型草案

```sql
-- admin_users 表
CREATE TABLE admin_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    open_id         VARCHAR(64) UNIQUE,           -- 飞书 OpenID（运营人员）
    name            VARCHAR(50) NOT NULL,
    email           VARCHAR(100),
    role            VARCHAR(20) NOT NULL,         -- operator / reviewer / admin
    department      VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'active', -- active / suspended / deleted
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    created_by      UUID,
    deleted_at      TIMESTAMPTZ,
    CHECK (role IN ('operator', 'reviewer', 'admin')),
    CHECK (status IN ('active', 'suspended', 'deleted'))
);

-- audit_log 表（关联 admin_users.id 而非 user.id）
ALTER TABLE safety_audit_logs ADD COLUMN operator_id UUID REFERENCES admin_users(id);
```

---

## 四、运营后台最小功能（MVP）

### 4.1 工作台首页（Home）

**布局**：
```
+------------------------------------------------------------+
| Selfwell 运营后台        运营: 张三 v  [退出登录]             |
+------------+-----------------------------------------------+
|            |                                                |
| 工作台     |   +---------+  +---------+  +---------+       |
| 审核      |   | 待审核:  |  | 待处理:  |  | 危机:    |       |
| 活动      |   |   12    |  |    3    |  |   0     |       |
| 词库      |   +---------+  +---------+  +---------+       |
| 报告      |                                                |
| 日志      |   最近 7 天合规率趋势图                         |
|            |   [█████████░░░░] 96.3%                      |
+------------+-----------------------------------------------+
```

**核心组件**：
- 待办卡片（待审核/待处理/危机）
- 合规率趋势图（最近 7/30 天）
- 最近危机事件列表（reviewer/admin 可见）

### 4.2 社区审核队列（P1-BE-03）

| 字段 | 来源 | 操作 |
|------|------|------|
| 内容预览 | community_posts | - |
| 命中关键词 | L1 扫描结果 | - |
| LLM 分类结果 | L2 分类 | - |
| 提交时间 | posts.created_at | - |
| 提交用户 | users.nickname（脱敏） | - |
| 操作 | - | [通过] [拒绝] [查看原文] |

**关键交互**：
- 拒绝时弹出原因选择（医疗引导 / 颜值评判 / 效果承诺 / 政治敏感 / 其他）
- 通过/拒绝后写入 `community_moderation_logs`（操作人 + 时间 + 原因）
- 危机内容标红置顶（reviewer 优先处理）

### 4.3 活动发布（P1-BE-04）

| 字段 | 类型 | 说明 |
|------|------|------|
| 活动标题 | string | 30 字以内 |
| 活动封面 | image | 16:9，自动压缩 |
| 活动正文 | rich text | 富文本编辑器 |
| 开始/结束时间 | datetime | - |
| 目标用户群 | enum | 全部 / 新用户 / 老用户 / 21 天计划用户 |
| 推送通道 | multi-select | 站内 / 微信小程序订阅消息 / 微信服务通知 |
| 状态 | enum | 草稿 / 待审核 / 已发布 / 已下架 |

**权限**：operator + admin 可创建/编辑；admin 审核发布

---

## 五、ADR 编号分配（待补）

| ADR | 标题 | 关联 |
|-----|------|------|
| **ADR-0020**（占位） | RBAC 权限体系（4 类角色） | §三 |
| **ADR-0021**（占位） | 运营后台技术栈（Vue3 + Element Plus） | §四 |
| **ADR-0022**（占位） | 敏感词库版本管理 | TDS-M14 §5.3 |

---

## 六、P1 排期建议

| 周次 | 任务 |
|------|------|
| **W1** | ADR-0020/0021/0022 评审 → P1-BE-01 RBAC 实施 → P1-BE-09 L1 合规引擎 |
| **W2** | P1-BE-02 运营工作台骨架 → P1-BE-03 审核队列 → P1-FE-01 危机响应卡组件化 |
| **W3** | P1-BE-05 敏感词管理 → P1-BE-10 L3 输出网关 → P1-BE-11 L-Crisis 同步拦截 |
| **W4** | P1-FE-02/03 L-Serious/L-Medical 响应卡 → P1-FE-04/05 社区/日记合规提示 → 联调 |

---

## 七、合规 Gap 分析详情

### 7.1 MVP 前端已有（当前 sprint 实现）

| 功能 | 前端节点 | ATDD 来源 | PRD 来源 |
|------|---------|----------|----------|
| L-Crisis 危机响应卡 | 节点 30 | ATDD-Compliance §三 L-Crisis | PRD §3.5.2 |
| 隐私协议前置弹窗 | 节点 31 | ATDD-Auth §零 | PRD §1.0 |
| 隐私政策页面 | 节点 20 | ATDD-Auth §零 | PRD §1.0 |
| 基线问候模板池（4 档） | 节点 0 | PRD §1.4 | PRD §1.4 |
| 打卡完成合规文案（无量化） | 节点 11 | PRD §3.2 | PRD §3.2 |
| 打卡完成无效果承诺 | 节点 11 | PRD §1.8 | PRD §1.8 |

### 7.2 P1 前端缺失（需新建设计稿）

| 功能 | 建议设计稿 | ATDD 来源 | 说明 |
|------|-----------|----------|------|
| L-Serious 严重情绪响应卡 | 复用节点 30 风格 | ATDD-Compliance §三 | 三级危机分级之一 |
| L-Medical 医疗急迫响应卡 | 复用节点 30 风格 | ATDD-Compliance §三 | 三级危机分级之一 |
| 社区发布前合规提示弹窗 | 新建节点 | ATDD-Compliance §一 L4 | 增强合规感知 |
| 智能管家对话 L-Crisis 触发 | 复用节点 30 | ATDD-Compliance §三 | 复用危机响应卡 |
| 社区内容发布合规引导页 | 新建节点 | ATDD-Compliance §一 | 三段式审核前置 |
| 心情日记合规提示 | 新建节点 | ATDD-Compliance §二 | 引导用户避免违规 |

### 7.3 P1 后端缺失（需新建 API/Service）

| 功能 | 验收来源 | 说明 |
|------|----------|------|
| L1 合规引擎（BloomFilter + PG 精确匹配） | ATDD-Compliance §一 L1 | MVP 上线前必须实现 |
| L3 输出网关（Middleware + BloomFilter） | ATDD-Compliance §一 L3 | 流式输出安全拦截 |
| L-Crisis 同步阻塞（<50ms） | ATDD-Compliance §三 | 危机词表最高优先级 |
| L-Serious/L-Medical 异步分类 | ATDD-Compliance §三 | 可复用 LLM 分类服务 |
| safety_audit_logs 记录 | TDS-M14 §5.1 | 不含对话原文 |
| sensitive_words 表 + 版本管理 | ATDD-Compliance §七 | 敏感词 CRUD |

---

## 八、修订历史

| 日期 | 版本 | 改动 | 来源 |
|------|------|------|------|
| 2026-07-21 | V0.1 | 初次创建：识别无前端页面功能 + RBAC 草案 + P1 排期 | ATDD-Compliance / TDS-M14 梳理 |
| 2026-07-22 | V0.3 | 新增 §1.2 合规功能前端已有 vs 缺失分析；新增 §2.2 前端能力清单；新增 §7 合规 Gap 分析详情；更新 P1-BE-09~11 合规引擎后端任务 | TDS-M14 / ATDD-Compliance / 前端设计稿对比 |
