from functools import wraps
from flask import g
from typing import Any, Dict, TypeVar, Generic, Callable, Awaitable, ParamSpec
import inspect


T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")


class Depend(Generic[T]):
    def __init__(self, dependency: Callable[..., T], use_cache: bool = True) -> None:
        self.dependency = dependency
        self.use_cache = use_cache

    @classmethod
    def __class_getitem__(cls, item: Dict[Any, Any]):
        return cls


def resolve_dependencies(
    view_func: Callable[P, R | Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    sig = inspect.signature(view_func)
    dep_map = {
        name: param.default
        for name, param in sig.parameters.items()
        if isinstance(param.default, Depend)
    }

    async def get_value(dep_obj: Depend) -> Any:
        dep_func = dep_obj.dependency
        if dep_obj.use_cache and dep_func in g._nova_deps:
            return g._nova_deps[dep_func]
        sub_sig = inspect.signature(dep_func)
        sub_kwargs = {}
        for sub_name, sub_param in sub_sig.parameters.items():
            if isinstance(sub_param.default, Depend):
                sub_kwargs[sub_name] = await get_value(sub_param.default)
        if inspect.iscoroutinefunction(dep_func):
            result = await dep_func(**sub_kwargs)
        else:
            result = dep_func(**sub_kwargs)

        if dep_obj.use_cache:
            g._nova_deps[dep_func] = result
        return result

    @wraps(view_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not hasattr(g, "_nova_deps"):
            g._nova_deps = {}

        for name, dep_obj in dep_map.items():
            kwargs[name] = await get_value(dep_obj)

        if inspect.iscoroutinefunction(view_func):
            return await view_func(*args, **kwargs)
        return view_func(*args, **kwargs)  # type: ignore

    return wrapper
