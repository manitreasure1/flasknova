from enum import Enum
import inspect as ip
import functools as ft
import typing as t
from flask import request
from .utils import filter_options
from .responses import bind_route_parameters, ResponseSerializer
from . import types as nt
from .di import resolve_dependencies
from .exceptions import HTTPException


P = t.ParamSpec("P")
R = t.TypeVar("R")


class RouteFactory:
    def __init__(self, serializer: ResponseSerializer) -> None:
        self.serializer = serializer

    def build(
        self,
        owner: t.Any,
        rule: str,
        methods: t.List[nt.Method],
        tags: t.Optional[t.List[t.Union[str, Enum]]],
        response_model: t.Any | None,
        summary: t.Optional[str] = None,
        description: t.Optional[str] = None,
        responses: dict[str, t.Any] | None = None,
        servers: list[str] | None = None,
        mermaid: str | None = None,
        provide_automatic_options: bool | None = None,
        **options: t.Dict[str, t.Any],
    ) -> t.Callable[[nt.T_route], nt.T_route]:

        def decorator(func: nt.T_route) -> nt.T_route:
            sig = ip.signature(func)
            type_hints = t.get_type_hints(func)

            f = resolve_dependencies(func)

            setattr(f, "_flasknova_tags", tags or [])
            setattr(f, "_flasknova_response_model", response_model)
            setattr(f, "_flasknova_summary", summary)
            setattr(f, "_flasknova_description", description)
            setattr(f, "_flasknova_responses", responses)
            setattr(f, "_flasknova_route_servers", servers)
            setattr(f, "_flasknova_mermaid", mermaid)

            @ft.wraps(f)
            async def handler(*args: t.Any, **kwargs: dict[str, t.Any]):
                bound_values = await bind_route_parameters(f, sig, type_hints)
                if isinstance(bound_values, tuple):
                    return bound_values

                try:
                    result = await f(**bound_values)
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))

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
