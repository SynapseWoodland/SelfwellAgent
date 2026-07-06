Feature: Exception Handler Middleware — 统一异常映射

  Scenario: SelfwellError 子类返回对应 HTTP 状态码
    Given 自定义错误 CustomError(HttpStatus=422)
    When 路由抛出 CustomError
    Then 响应 HTTP 422
    And 响应体含 error.code = "E_CUSTOM"
    And 响应体含 error.message_zh

  Scenario: 未知异常返回 500 + 通用错误码
    Given 路由抛出未捕获的 RuntimeError
    When 请求到达中间件
    Then 响应 HTTP 500
    And 错误码 = "E_GENERAL_INTERNAL_ERROR"
    And message_zh = "服务端错误，请稍后重试"

  Scenario: SelfwellError 携带 traceback 日志
    Given 触发 SelfwellError 的请求
    When 异常被中间件捕获
    Then 日志包含完整 traceback
    And 日志包含 error.code
    And 日志包含 request.path

  Scenario: 5xx 响应携带 X-Request-ID 头
    Given 请求触发 500 错误
    When 异常中间件处理
    Then 响应头含 X-Request-ID 或 traceparent

  Scenario: E_GENERAL_RATE_LIMIT 响应格式正确
    Given RateLimitMiddleware 触发
    When 返回 429 响应
    Then 响应体为 JSON {error: {code, message_zh, message_en}}
    And 错误码 = "E_GENERAL_RATE_LIMIT"

  Scenario: 异常中间件不吞掉 SelfwellError 的 http_status
    Given SelfwellError 子类 http_status=403
    When 抛出该异常
    Then 响应 HTTP 403（不是默认的 500）
