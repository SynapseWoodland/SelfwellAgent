"""Result 类型 Sugar（Sprint 0 骨架）。

提供 ``ok`` / ``err`` 构造器与 ``@safe`` 装饰器；与 ``core.errors.Ok`` / ``Err`` 协作。

参考设计：Rust ``std::result`` 与 Scala ``Either`` 的人体工学参考。
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar

from app.core.errors import Err, Ok, Result

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
E = TypeVar("E")


def ok[T](value: T) -> Ok[T]:
    """构造 ``Ok``（成功分支）。"""
    return Ok(value)


def err[E](error: E) -> Err[E]:
    """构造 ``Err``（失败分支）。"""
    return Err(error)


def safe(
    *exc_types: type[BaseException],
    mapper: Callable[[BaseException], Any] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., Result[T, BaseException]]]:
    """装饰器：把函数返回值包成 ``Result``，异常 → ``Err``。

    Args:
        *exc_types: 捕获的异常类型；默认 ``Exception``。
        mapper: 自定义异常 → 错误对象映射；默认 ``lambda e: e``。

    Example:
        >>> @safe(ValueError)
        ... def parse_int(s: str) -> Result[int, BaseException]:
        ...     return int(s)

    """

    def decorator(func: Callable[..., T]) -> Callable[..., Result[T, BaseException]]:
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> Result[T, BaseException]:
            try:
                return Ok(func(*args, **kwargs))
            except BaseException as e:
                if exc_types and not isinstance(e, exc_types):
                    raise
                return Err(mapper(e) if mapper else e)

        return wrapper

    return decorator


__all__ = ["Result", "err", "ok", "safe"]
