"""SelfwellAgent 测试集根目录。

下分两个子包，**职责严格不混装**：

| 子包 | 职责 | 落点 |
| --- | --- | --- |
| `intercept` | 输入拦截 + 输出检测（pytest） | ``backend/tests/intercept/`` |
| `eval` | 业务路由回归（pytest 单测） | ``backend/tests/eval/`` |

业务路由 Golden Set（YAML + Runner）位于 ``backend/eval/``，与本目录同级。
"""