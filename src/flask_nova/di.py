from functools import wraps
from flask import g
from typing import TypeVar, Generic, Callable
import inspect


T = TypeVar("T")


class Depend(Generic[T]):
    def __init__(self, dependency: Callable[..., T]):
        self.dependency = dependency

    @classmethod
    def __class_getitem__(cls, item):
        return cls


def resolve_dependencies(view_func):
    sig = inspect.signature(view_func)

    @wraps(view_func)
    async def wrapper(*args, **kwargs):
        if not hasattr(g, "_nova_deps"):
            g._nova_deps = {}

        for name, param in sig.parameters.items():
            default = param.default
            if isinstance(default, Depend):
                dep_func = default.dependency
                if dep_func not in g._nova_deps:
                    if inspect.iscoroutinefunction(dep_func):
                        g._nova_deps[dep_func] = await dep_func()
                    else:
                        g._nova_deps[dep_func] = dep_func()
                kwargs[name] = g._nova_deps[dep_func]

        if inspect.iscoroutinefunction(view_func):
            return await view_func(*args, **kwargs)
        return view_func(*args, **kwargs)

    return wrapper
