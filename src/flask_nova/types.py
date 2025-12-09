from __future__ import annotations

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Literal,
    Mapping,
    Optional,
    Protocol,
    TypeVar,
    Union,
    Mapping,
    Tuple
)


DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])

# HTTP method literal for route decorators
Method = Literal["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]



class NovaResponse(Protocol):
    """HTTP response contract for Nova handlers."""
    status_code: int
    headers: Mapping[str, str]
    body: Any
    content_type: Optional[str]
    reason_phrase: Optional[str]
    cookies: Optional[Mapping[str, str]]

# Generic return type used in handler signatures
RouteReturn = Union[
    str,
    Dict[str, Any],
    bytes,
    int,
    float,
    list[Any],
    NovaResponse,
    Tuple[Any, int],
    Tuple[Any, int, Mapping[str, str]],
]



# Sync/async handler types
SyncRouteHandler = Callable[..., RouteReturn]
AsyncRouteHandler = Callable[..., Awaitable[RouteReturn]]


# A "RouteHandler" can be a sync or async callable (we treat them separately during dispatch)
RouteHandler = Union[SyncRouteHandler, AsyncRouteHandler]




FLASK_TO_OPENAPI_TYPES = {
    "string": ("string", None),
    "int": ("integer", None),
    "float": ("number", None),
    "uuid": ("string", "uuid"),
    "path": ("string", None),
    "any": ("string", None),
}