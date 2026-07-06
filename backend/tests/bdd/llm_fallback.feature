Feature: LLM Fallback Chain — 4 级降级链

  Scenario: 主 LLM 可用时直接返回
    Given FallbackChain 已初始化（use_mock=False）
    And 主 LLM provider 可达
    When 调用 chain.run(request)
    Then 返回 FallbackResult
    And provider_used = 主模型名
    And attempts = 1

  Scenario: 主 LLM 失败自动降级到备 1
    Given FallbackChain 已初始化
    And 主 LLM 超时
    When 调用 chain.run(request)
    Then 返回 FallbackResult
    And provider_used = 备 1 模型名
    And attempts = 2

  Scenario: 全部 LLM 失败走规则引擎兜底
    Given FallbackChain 已初始化
    And 所有 4 级 LLM 均不可达
    When 调用 chain.run(request)
    Then 返回 FallbackResult
    And provider_used = "rule-engine"
    And content 含兜底文案
    And attempts = 4

  Scenario: 每次调用前触发 BudgetGuard.check()
    Given FallbackChain 初始化时 BudgetGuard 可用
    And 日预算未超限
    When 调用 chain.run
    Then 不抛出 BudgetExceededError
    And 调用前执行 check()

  Scenario: 日预算超限立即拒绝（不走降级链）
    Given BudgetGuard 日预算已耗尽
    When 调用 chain.run
    Then 抛出 BudgetExceededError
    And 不触发任何 LLM 调用
    And HTTP 503

  Scenario: 月预算超限触发 MonthlyBudgetExceededError
    Given BudgetGuard 月预算已耗尽
    And 日预算充足
    When 调用 chain.run
    Then 抛出 MonthlyBudgetExceededError
    And provider_used = "rule-engine"
    And HTTP 200（降级处理）
