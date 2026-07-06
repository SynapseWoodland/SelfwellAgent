Feature: Config & App Bootstrap — 配置加载与生命周期

  Scenario: app_config 加载 .env 配置
    Given .env 文件存在且配置完整
    When app_config 模块被导入
    Then 所有配置项（db/redis/llm/wechat）正确加载
    And 无默认值覆盖真实配置

  Scenario: JWT 配置不完整时拒绝启动
    Given JWT_SECRET_KEY 未配置或 < 32 字符
    When 尝试签发 token
    Then 抛出 JWTError
    And 错误码 = "E_GENERAL_INTERNAL_ERROR"

  Scenario: FastAPI lifespan 启动期初始化日志
    Given app 实例化时 lifespan 已注册
    When uvicorn 启动 app
    Then setup_logging() 在 lifespan 入口执行
    And 日志级别按 app_config.log_level 配置

  Scenario: FastAPI lifespan 收尾期释放资源
    Given 应用正在运行
    When uvicorn 收到 SIGTERM
    Then lifespan 退出块执行
    And dispose_engine() 被调用

  Scenario: 中间件按正确顺序挂载
    Given 三个中间件（Trace/Exception/RateLimit）
    When app.add_middleware 按配置顺序调用
    Then RateLimit 最内层（最先 add）
    And TraceContext 最外层（最后 add）
    And 请求处理顺序：Trace → Exception → RateLimit → Handler

  Scenario: Swagger UI 可访问
    Given 后端已启动
    When 访问 GET /docs
    Then 返回 HTML 文档页面
    And OpenAPI schema 可通过 /openapi.json 获取
