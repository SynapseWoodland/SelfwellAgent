Feature: Storage Abstraction — COS/MinIO 对象存储切换

  Scenario: MinIO 实现正常上传文件
    Given MinIO 配置完整（endpoint/access_key/secret_key/bucket）
    And 准备上传的文件内容
    When 调用 storage_impl.put_object(key, content)
    Then 文件成功上传到指定 bucket
    And 返回 object_url

  Scenario: COS 实现正常上传文件
    Given COS 配置完整（secret_id/secret_key/bucket/region）
    And 准备上传的文件内容
    When 调用 cos_impl.put_object(key, content)
    Then 文件成功上传到 COS bucket
    And 返回 object_url

  Scenario: 存储后缀路径生成规则
    Given 上传文件 key = "uploads/photo.jpg"
    When 生成最终存储路径
    Then 包含日期前缀 "uploads/2026/07/photo.jpg"
    And 保持原始文件扩展名

  Scenario: 存储抽象层统一接口
    Given StorageBackend 抽象类定义 put_object/get_object/delete_object
    When MinIOImpl 和 COSImpl 均实现该抽象
    Then 可通过 StorageBackend[MinIOImpl] 实例化
    And 切换实现不影响业务层调用

  Scenario: 文件不存在时 get_object 抛出 FileNotFoundError
    Given 存储中存在不存在的 key
    When 调用 get_object("nonexistent-key")
    Then 抛出 FileNotFoundError 或等价异常

  Scenario: 删除文件成功
    Given 存储中存在文件
    When 调用 delete_object(key)
    Then 文件从 bucket 中移除
    And 后续 get_object 该 key 抛出异常
