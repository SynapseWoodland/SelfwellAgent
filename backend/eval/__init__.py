"""SelfwellAgent Business Routing Eval.

业务路由回归（user → 路由节点 → response）的骨架入口。

**职责**：装在 ``backend/eval/golden_set_v1.yaml`` 的"自然语言 → 路由"用例回归。
**不负责**：拦截回归（属 ``backend/tests/intercept/``）。
"""