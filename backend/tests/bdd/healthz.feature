Feature: Healthz Probe — 三段探针决策树

  Scenario: 所有依赖服务（db/redis/llm）均可达
    Given 后端服务已启动
    And PostgreSQL 可达
    And Redis 可达
    And 所有 LLM provider 可达
    When 客户端请求 GET /healthz
    Then HTTP 响应状态码为 200
    And 响应体 status = "ok"
    And checks.db = "ok"
    And checks.redis = "ok"
    And checks.llm = "ok"

  Scenario: PostgreSQL 不可达时返回 503
    Given 后端服务已启动
    And PostgreSQL 不可达
    And Redis 可达
    When 客户端请求 GET /healthz
    Then HTTP 响应状态码为 503
    And 响应体 status = "down"
    And checks.db = "down"

  Scenario: Redis 不可达时返回 503
    Given 后端服务已启动
    And PostgreSQL 可达
    And Redis 不可达
    When 客户端请求 GET /healthz
    Then HTTP 响应状态码为 503
    And 响应体 status = "down"
    And checks.redis = "down"

  Scenario: 仅 LLM 降级时返回 200（degraded）
    Given 后端服务已启动
    And PostgreSQL 可达
    And Redis 可达
    And LLM provider 不可达
    When 客户端请求 GET /healthz
    Then HTTP 响应状态码为 200
    And 响应体 status = "degraded"
    And checks.llm = "degraded"

  Scenario: 三段探针并发执行（性能要求）
    Given 后端服务已启动
    And 所有依赖服务配置为 100ms 响应
    When 客户端请求 GET /healthz
    Then 总响应时间 < 500ms
    And 三段探针同时执行

  Scenario: 探针超时降级处理
    Given 后端服务已启动
    And Redis 配置为 3s 响应（超限）
    When 客户端请求 GET /healthz
    Then 探针在 2s 内超时
    And checks.redis = "down"
    And HTTP 响应状态码为 503
