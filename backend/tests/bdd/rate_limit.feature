Feature: Rate Limit — IP 级别令牌桶限流

  Scenario: 正常请求不触发限流
    Given 限流器配置 capacity=120, refill=2.0/s
    When 客户端首次请求
    Then 返回正常响应
    And 未设置 Retry-After 头

  Scenario: 超过速率限制返回 429
    Given 限流器配置 capacity=5, refill=1.0/s
    When 客户端快速发送 6 个请求
    Then 第 6 个请求返回 HTTP 429
    And 响应体 code = "E_GENERAL_RATE_LIMIT"
    And message_zh 含"请稍后重试"

  Scenario: 令牌桶逐步补充后恢复
    Given 触发限流后等待 3 秒
    And 令牌桶 refill=1.0/s
    When 客户端再发请求
    Then 返回正常响应

  Scenario: 不同 IP 独立限流
    Given 客户端 A 和客户端 B
    And 共享同一个限流器实例
    When 客户端 A 耗尽令牌
    Then 客户端 B 不受影响

  Scenario: Retry-After 精确秒数场景
    Given 限流触发，message 含 "{seconds}"
    When 计算 compute_retry_after_seconds(message_zh)
    Then 返回 60 秒

  Scenario: Retry-After 分钟级场景
    Given 限流文案含 "5 分钟"
    When 计算 compute_retry_after_seconds
    Then 返回 300 秒
