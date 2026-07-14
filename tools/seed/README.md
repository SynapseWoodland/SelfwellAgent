# Data Governance Seed Scripts

## 用途
为 Phase 4 测试（Golden Set、单测、E2E）准备充足的 PostgreSQL 数据。

## 覆盖表

| 脚本 | 目标表 | 目标条数 | 说明 |
|------|--------|---------|------|
| `seed_plans.py` | plans | 10 | 2 用户 × 5 方案 |
| `seed_checkins.py` | checkins | 42 | 2 用户 × 21 天 × 1 checkin/天 |
| `seed_feedback.py` | feedback | 30 | 21 天历史心情数据，覆盖 mood_text/mood_photo/period_photo |
| `seed_recall_sessions.py` | recall_sessions | 5 | user_query×2 + auto_day7 + auto_day14 + auto_day21 |
| `seed_posts.py` | posts | 10 | 蜕变广场社区动态 |
| `seed_videos.py` | videos | 7 | 7 条 seed videos（与 8 条现有合计 15） |
| `add_source_column.py` | - | - | 为 plans/checkins/feedback/recall_sessions/posts 添加 source 列 |
| `add_source_column_reports.py` | reports | - | 为 reports 添加 source 列并标注历史数据 |
| `verify_all.py` | - | - | 全表行数 + 业务验证 |

## 使用方法

### 一键执行所有 seed 脚本
```bash
python tools/seed/run_all.py
```

### 单个脚本执行
```bash
.venv/Scripts/python.exe tools/seed/seed_plans.py
.venv/Scripts/python.exe tools/seed/seed_checkins.py
...
```

### 仅做验证
```bash
.venv/Scripts/python.exe tools/seed/verify_all.py
```

## 重要说明

### 数据库连接
所有脚本使用以下连接信息（来自 `backend/.env`）：
- Host: `localhost`
- Port: `5432`
- Database: `selfwell`
- User: `selfwell`
- Password: `change_me_in_dev_only`

### 幂等性
所有 seed 脚本均**幂等**：
- 第一次运行：清空目标表 → 插入 seed 数据
- 第二次运行：清空 → 重新插入 → 数据条数不变

可连续执行 `python tools/seed/run_all.py` 多次验证。

### Schema 约束
- `feedback.body_part`：枚举值 = `face, head, shoulder_neck, waist, leg, overall_look`
- `feedback.feedback_type`：枚举值 = `mood_text, mood_photo, period_photo, plan_compare_photo`
- `recall_sessions.trigger`：枚举值 = `user_query, auto_day7, auto_day14, auto_day21`
- `recall_sessions.ai_encourage`：≤ 80 字符
- `recall_sessions.ai_summary`：≤ 200 字符
- `checkins`：唯一约束 `(user_id, plan_id, day)`，所以每个用户每天只能 1 条

### 数据分类
- **真实用户**：2 个微信账号（`platform=wx_mp`），UUID 保持不变
- **Seed 标记**：所有 seed 数据通过 `source='seed'` 字段标记，可单独查询/清理
- **历史报告**：
  - `source='mock-rule-engine'`：16 条 rule-engine mock 数据
  - `source='demo-model'`：1 条 demo 模型数据
  - `source='pending'`：10 条 LLM 处理中

### 执行顺序依赖
1. `add_source_column.py` （先添加列）
2. `seed_plans.py` （必须最先，checkins 依赖 plan_id）
3. `seed_checkins.py` （依赖 plans）
4. 其他 4 个 seed 脚本（相互独立，可并行）
5. `add_source_column_reports.py` （标注历史数据）

## 验证结果（2026-07-13）

```
[1] Table row counts:
  users: 2 (preserved)
  plans: 10 (D5-1)
  checkins: 42 (D6-1)
  recall_sessions: 5 (D7-1)
  feedback: 30 (D8-1)
  posts: 10 (D9-1)
  videos: 15 (D10-1, 8 existing + 7 seed)
  reports: 27 (D4, with source labeling)

[8] Acceptance criteria:
  [PASS] plans >= 10: 10
  [PASS] checkins >= 42: 42
  [PASS] recall_sessions >= 5: 5
  [PASS] feedback >= 30: 30
  [PASS] posts >= 10: 10
  [PASS] videos >= 15: 15
```