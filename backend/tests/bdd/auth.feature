Feature: JWT Authentication — Token 签发与校验

  Scenario: 正常签发 JWT access token
    Given JWT 配置就绪（secret_key >= 32 字符）
    And 用户 user_id = "test-user-uuid"
    When 调用 sign_access_token(user_id="test-user-uuid")
    Then 返回非空 token 字符串
    And token 可被 decode_token 解析
    And payload["sub"] = "test-user-uuid"
    And payload["type"] = "access"

  Scenario: JWT 配置未就绪时签发失败
    Given JWT 配置未就绪（secret_key 未配置）
    When 调用 sign_access_token(user_id="test-user-uuid")
    Then 抛出 JWTError 异常
    And 错误码 = "E_GENERAL_INTERNAL_ERROR"
    And HTTP 状态码 = 500

  Scenario: 正常校验有效 token
    Given 有效的 JWT token
    When 调用 decode_token(token)
    Then 返回完整 payload 字典
    And payload["sub"] = 用户 ID

  Scenario: 校验已过期 token 抛出 JWTExpiredError
    Given 已过期的 JWT token（exp < now）
    When 调用 decode_token(token, verify_exp=True)
    Then 抛出 JWTExpiredError
    And 错误码 = "E_AUTH_TOKEN_EXPIRED"
    And HTTP 状态码 = 401

  Scenario: 校验伪造签名 token 抛出 JWTInvalidSignatureError
    Given 用错误密钥签发的 JWT token
    When 调用 decode_token(token)
    Then 抛出 JWTInvalidSignatureError
    And 错误码 = "E_AUTH_TOKEN_INVALID"

  Scenario: decode_token 跳过过期校验
    Given 已过期的 JWT token
    When 调用 decode_token(token, verify_exp=False)
    Then 返回 payload（不抛异常）
    And payload["sub"] = 用户 ID
