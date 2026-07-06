Feature: Trace Context Middleware — 分布式链路追踪

  Scenario: 首次请求生成新的 trace ID
    Given 客户端首次请求（无 X-Request-ID 头）
    When 请求经过 TraceContextMiddleware
    Then 响应头 X-Request-ID 已设置
    And X-Request-ID 为有效 UUID 格式

  Scenario: 上游传递 trace ID 时透传
    Given 请求头含 X-Request-ID = "existing-trace-id"
    When 请求经过 TraceContextMiddleware
    Then 响应头 X-Request-ID = "existing-trace-id"
    And 不生成新的 trace ID

  Scenario: traceparent 头格式兼容 W3C 标准
    Given 请求头含 traceparent
    When 解析 traceparent
    Then 可提取 trace-id 和 span-id
    And 格式为 "00-{trace-id}-{span-id}-01"

  Scenario: 错误响应仍包含 trace ID
    Given 触发 500 错误的请求
    When 异常中间件处理后
    Then 错误响应仍含 X-Request-ID
    And 可用于日志关联

  Scenario: 快速路径：无需处理时跳过追踪开销
    Given 简单的内部请求
    When TraceContextMiddleware 判断无需追踪
    Then 最小化中间件处理时间

  Scenario: trace context 注入到日志上下文
    Given 带 trace ID 的请求
    When 业务逻辑记录日志
    Then 日志自动包含 trace_id 字段
    And 可通过 trace_id 过滤同一请求的日志
