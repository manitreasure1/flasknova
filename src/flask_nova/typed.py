from __future__ import annotations
import typing as t

from flask.wrappers import Response

P = t.ParamSpec("P")
R = t.TypeVar("R")


class FormMarker:
    def __init__(self, type_: type | None = None) -> None:
        self.type_ = type_


class FileMarker:
    def __init__(self, name: str, multiple: bool = False) -> None:
        self.name = name
        self.multiple = multiple


Method = t.Literal["GET", "POST", "PUT", "DELETE", "PATCH"]

FuncType = t.Callable[P, R]
Decorated = t.Callable[P, R | Response]
Guard = t.Callable[[FuncType], Decorated]
