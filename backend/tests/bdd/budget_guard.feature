Feature: Budget Guard — LLM 月/日预算守卫

  Scenario: 日预算充足时允许调用
    Given BudgetGuard 初始化
    And 当前日消耗 = 0
    And 日预算上限 = 40 元
    When 调用 budget_guard.check(estimated_cost=10.0)
    Then 不抛出异常

  Scenario: 日预算超限时抛出 BudgetExceededError
    Given BudgetGuard 日消耗已接近上限
    When 调用 budget_guard.check(estimated_cost=50.0)
    Then 抛出 BudgetExceededError
    And 错误码 = "E_GENERAL_SERVICE_UNAVAILABLE"
    And HTTP 状态码 = 503

  Scenario: 日重置后恢复使用
    Given 日预算已耗尽（触发限额）
    When 调用 reset_daily()
    And 调用 budget_guard.check(estimated_cost=1.0)
    Then 不抛出异常

  Scenario: 月预算超限触发降级错误
    Given BudgetGuard 月消耗已超过 700 元
    When 调用 budget_guard.check(estimated_cost=1.0)
    Then 抛出 MonthlyBudgetExceededError
    And HTTP 状态码 = 200（降级处理）

  Scenario: record 累积日/月成本
    Given 当前日消耗 = 0
    When 调用 budget_guard.record(cost_yuan=15.0)
    Then daily_cost = 15.0
    And monthly_cost = 15.0

  Scenario: 跨日自动重置日预算
    Given 日预算已消耗 30 元
    When 时间推进到次日
    And 调用 check(estimated_cost=5.0)
    Then daily_cost 从 0 开始计算
    And 不抛出日预算超限
