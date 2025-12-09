from enum import Enum
import inspect as ip
import functools as ft
import typing as t
from flask import request

from .utils import filter_options
from .responses import _bind_route_parameters, ResponseSerializer
from . import types as nt

from .di import resolve_dependencies

class RouteFactory:
    def __init__(self, serializer: ResponseSerializer):
        self.serializer = serializer

    def build(
            self,
            owner,
            rule: str,
            methods: t.List[nt.Method],
            tags: t.Optional[t.List[t.Union[str, Enum]]],
            response_model: t.Any| None,
            summary: t.Optional[str]= None,
            description: t.Optional[str]= None,
            provide_automatic_options: bool | None = None,
            **options):


        def decorator(func):
            is_async = ip.iscoroutinefunction(func)
            sig = ip.signature(func)
            type_hints = t.get_type_hints(func)

            f = resolve_dependencies(func)


            setattr(f, "_flasknova_tags", tags or [])
            setattr(f, "_flasknova_response_model", response_model)
            setattr(f, "_flasknova_summary", summary)
            setattr(f, "_flasknova_description", description)


            @ft.wraps(f)
            async def handler(*args, **kwargs):
                bound_values = await _bind_route_parameters(f, sig, type_hints)
                if isinstance(bound_values, tuple):
                    return bound_values

                try:
                    result = await f(**bound_values) if is_async else f(**bound_values)
                except Exception as e:
                    raise e

                return self.serializer.serialize(result, response_model, request)

            flask_options = filter_options(func, options=options)

            owner.add_url_rule(
                rule=rule,
                endpoint=func.__name__,
                view_func=handler,
                methods=methods,
                provide_automatic_options=provide_automatic_options,
                **flask_options,
            )

            return func

        return decorator
