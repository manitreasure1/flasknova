from functools import wraps
from flask import g
import inspect


from typing import TypeVar, Generic, Callable

T = TypeVar("T")

class Depend(Generic[T]):
    def __init__(self, dependency: Callable[..., T]):
        self.dependency = dependency

    @classmethod
    def __class_getitem__(cls, item):
        return cls


def resolve_dependencies(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(view_func)
        for name, param in sig.parameters.items():
            if isinstance(param.default, Depend):
                dep_func = param.default.dependency
                # Cache per request to avoid multiple calls
                if not hasattr(g, '_resolved_deps'):
                    g._resolved_deps = {}
                if dep_func not in g._resolved_deps:
                    g._resolved_deps[dep_func] = dep_func()
                kwargs[name] = g._resolved_deps[dep_func]
        return view_func(*args, **kwargs)
    return wrapper
