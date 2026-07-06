Feature: JWT Authentication — 认证流程完整测试

  Scenario: 微信小程序登录流程（骨架阶段）
    Given 微信授权码 js_code = "test-auth-code"
    And WeChatClient 已实例化
    When 调用 code2session(js_code)
    Then 返回包含 openid 的字典
    And openid 格式为 28 字符字符串

  Scenario: 微信授权码无效时抛出 WeChatClientError
    Given 无效的微信授权码
    When 调用 code2session(invalid_code)
    Then 抛出 WeChatClientError
    And 错误码 = "E_AUTH_CODE_INVALID"
    And HTTP 状态码 = 401

  Scenario: JWT Token 包含平台标识
    Given 用户从微信小程序登录
    When 签发 access_token(openid_mp=openid)
    Then token payload 包含 platform = "wechat"
    And token 可用于后续 API 请求鉴权

  Scenario: Token 携带额外 claims
    Given 用户登录时携带额外信息
    When 签发 access_token(extra_claims={"unionid": "test-union"})
    Then token payload 包含 unionid
    And decode_token 返回的 payload 包含 unionid

  Scenario: 自定义过期时间
    Given 需要短期 token（5 分钟）
    When 签发 access_token(expires_minutes=5)
    Then token 在 5 分钟后过期
    And 5 分钟后 decode_token 抛出 JWTExpiredError
