"""app.errors — 业务错误码模块（Sprint 0 骨架）。

唯一真源：``docs/api/error-codes.md`` + ``docs/api/openapi.yaml``
双向同步。

约定：
- 所有 ``E_*`` 常量必须从 ``from app.errors.codes import E_*`` 引用
- 禁止任何 ``agents/`` / ``nodes/`` / ``tools/`` / ``api/`` 直接写 ``E_*`` 字符串字面量
"""

from app.errors.codes import __all__  # intentional alias to lowercase dunder

__all__ = list(__all__)
