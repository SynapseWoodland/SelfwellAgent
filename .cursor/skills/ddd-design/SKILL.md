---
name: ddd-design
description: DDD 限界上下文设计方法论。当划分新 Context、设计 Aggregate、设计 Domain Event、或评估 Context 边界时触发。覆盖 6 Context 划分、12 Event 编排、Aggregate 强约束、目录骨架、反模式自审。
---

# DDD 设计 Skill

> 本 Skill 提供 Bounded Context / Aggregate / Domain Event 的设计方法论。
> 速查表：`.cursor/rules/ddd-bounded-context.mdc`
> 详细文档：`docs/architecture/ddd-bounded-context.md`

---

## 一、触发条件

| 场景 | 触发动作 |
|------|----------|
| 新建 Service/Module | 评估是否需要新 Context |
| 设计 Aggregate | 套用 Aggregate Root 铁律 |
| 跨 Service 调用 | 评估是否改为 Domain Event |
| 设计 API | 检查是否违反 Context 边界 |
| 重构现有 Service | 检查是否需要迁移到 `contexts/` 目录 |

---

## 二、设计流程

### Step 1: 识别 Bounded Context

**问题清单**：
1. 这个业务的"通用语言"是什么？用 1 句话描述
2. 这个业务的 Aggregate Root 是哪个？
3. 这个业务的核心不变式是什么？
4. 跨 Context 边界在哪？

**示例（Diagnosis Context）**：
- 通用语言："用户上传 3 张照片，AI 分析皮肤状态，生成诊断报告"
- Aggregate Root: `Diagnosis`
- 不变式：3 张照片必传 / 状态机 upload → analyzing → ready / 报告生成后状态不可改
- 边界：与 Plan Context 通过 `DiagnosisCompletedEvent` 通信

---

### Step 2: 设计 Aggregate Root

**铁律**：

| 铁律 | 含义 |
|------|------|
| 唯一入口 | 所有修改通过 Root 方法 |
| 事务边界 | 一个事务 = 一个 Aggregate |
| 跨 Context 引用 | 只传 ID，不传对象 |
| 不变性 | Root 校验业务规则 |

**模板**：

```python
@dataclass
class Diagnosis:
    id: UUID
    user_id: UUID          # 跨 Context 引用：只传 ID
    images: list[Image]
    status: DiagnosisStatus
    report: DiagnosisReport | None

    def start_analysis(self) -> None:
        """领域方法：触发状态机迁移"""
        if self.status != DiagnosisStatus.UPLOADED:
            raise InvalidStateTransition(...)
        self.status = DiagnosisStatus.ANALYZING
        # 发布 Event（在 Aggregate 内部）
        self._events.append(AnalysisStartedEvent(...))

    def complete(self, report: DiagnosisReport) -> None:
        if self.status != DiagnosisStatus.ANALYZING:
            raise InvalidStateTransition(...)
        self.report = report
        self.status = DiagnosisStatus.READY
        self._events.append(DiagnosisCompletedEvent(...))
```

---

### Step 3: 设计 Domain Event

**命名**：`{Aggregate}{动词过去式}Event`

**字段**（强制）：

```python
@dataclass(frozen=True)
class DiagnosisCompletedEvent:
    event_name: str = "DiagnosisCompletedEvent"
    aggregate_id: str          # Diagnosis.id
    occurred_at: datetime
    user_id: str               # 跨 Context 上下文
    direction_count: int       # 业务负载
```

**发布时机**：
- Aggregate 方法内 `self._events.append(...)`
- Service 层 `await event_bus.publish(...)`
- 事务提交后发送（避免回滚导致幽灵事件）

---

### Step 4: 设计 Event Handler

**骨架**：

```python
# app/contexts/notification/handlers.py
from app.events.bus import event_bus
from app.events.diagnosis_events import DiagnosisCompletedEvent


async def on_diagnosis_completed(event: DiagnosisCompletedEvent) -> None:
    """诊断完成后，通知用户查看报告。"""
    await send_notification(
        user_id=event.user_id,
        template="diagnosis_ready",
        payload={"diagnosis_id": event.aggregate_id},
    )


def register_handlers() -> None:
    event_bus.subscribe("DiagnosisCompletedEvent", on_diagnosis_completed)
```

**幂等性**：Handler 必须幂等（同 Event 多次投递不重复处理）。

---

## 三、6 个 Context 设计速查

### User Context
- **Aggregate**: `User`
- **核心 Event**: `UserRegisteredEvent`, `UserDeactivatedEvent`, `ConsentGrantedEvent`
- **Value Object**: `Nickname`, `Avatar`, `PrivacySettings`

### Diagnosis Context
- **Aggregate**: `Diagnosis`
- **核心 Event**: `DiagnosisCompletedEvent`, `DiagnosisFailedEvent`
- **Value Object**: `Image`, `Direction`, `Tag`, `Severity`

### Plan Context
- **Aggregate**: `TodayPlan`, `Task`, `Checkin`
- **核心 Event**: `PlanActivatedEvent`, `TaskAssignedEvent`, `CheckinSubmittedEvent`
- **Value Object**: `PlanDay`, `TaskType`, `TaskStatus`

### Community Context
- **Aggregate**: `Post`, `Comment`
- **核心 Event**: `PostCreatedEvent`, `PostModeratedEvent`
- **Value Object**: `Content`, `ModerationStatus`

### Video Context
- **Aggregate**: `Video`
- **核心 Event**: `VideoSearchedEvent`
- **Value Object**: `VideoUrl`, `FallbackStrategy`

### Notification Context
- **Aggregate**: `Notification`
- **核心 Event**: `NotificationSentEvent`
- **Value Object**: `Template`, `Channel`, `Payload`

---

## 四、反模式清单

| 反模式 | 正确做法 |
|--------|----------|
| Context A 直接 import Context B 的 Service | 通过 Domain Event |
| 跨 Context 共享数据库表 | 各自拥有数据，通过 Event 同步 |
| 一个事务更新多个 Aggregate | 拆分为多个事务 + Event 协调 |
| Aggregate 内包含外部 Context 的 Entity | 只持有 ID 引用 |
| 在 API 层手动编排多个 Service | 各 Context 独立 API，前端组合 |
| Event Handler 内调用 HTTP API（同步） | Handler 内只调用本地 Service |
| Event 命名 `user_event` / `on_diagnosis` | 命名 `{Aggregate}{动词}Event` |
| 跨 Context 传整个 User 对象 | 只传 `user_id: UUID` |
| Aggregate Root 没有不变量校验 | 在 Root 方法内 `if/raise` |

---

## 五、自审 Checklist

设计完成后必须逐项检查：

- [ ] 业务能力是否归属正确的 Context？
- [ ] Aggregate Root 是否有清晰的不变量？
- [ ] 跨 Context 通信是否都通过 Domain Event？
- [ ] Domain Event 命名是否符合规范？
- [ ] Event Handler 是否幂等？
- [ ] 是否有 Context 间共享数据库表？
- [ ] 目录结构是否符合 `contexts/<name>/{domain,application,infrastructure,interfaces}/`？
- [ ] 是否在 `app/events/handlers.py` 注册了所有 Handler？

---

## 六、迁移路径（从 services/ 到 contexts/）

### 阶段 1：新建模块按 contexts/ 组织

```bash
backend/app/contexts/
├── user/
│   ├── domain/user.py
│   ├── application/user_service.py
│   ├── infrastructure/user_repo.py
│   └── interfaces/user_router.py
```

### 阶段 2：现有 Service 渐进迁移

1. 在 `contexts/` 下创建新结构
2. 用 `from app.contexts.user import UserService as NewUserService` 兼容旧 import
3. 逐步将调用方迁移到新 import
4. 旧的 `services/user_service.py` 标记 DEPRECATED

### 阶段 3：清理

1. 删除旧 `services/` 目录
2. 更新所有 import
3. 更新测试 fixture

---

## 七、参考

- 速查表：`.cursor/rules/ddd-bounded-context.mdc`
- 详细文档：`docs/architecture/ddd-bounded-context.md`
- Eric Evans《Domain-Driven Design》
- Vaughn Vernon《Implementing Domain-Driven Design》
