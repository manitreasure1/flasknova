from __future__ import annotations
import typing as t
import warnings
from flask.wrappers import Response

P = t.ParamSpec("P")
R = t.TypeVar("R")


class FormMarker:
    def __init__(self, type_: type | None = None) -> None:
        self.type_ = type_


class FileMarker:
    """FileMarker origin for `cls:`File` request class object

    Args:
        name: the name of the file
        multiple: if it is list of files
        content_type: explicit content type for making the request
        descripton: helpful for api documentation
    """

    def __init__(
        self,
        name: str,
        multiple: bool = False,
        content_type: str | None = None,
        description: str | None = None,
    ) -> None:
        self.name = name
        self.multiple = multiple
        self.content_type = content_type
        self.description = description


def _deprecated(message: str):
    def decorator(function):
        return function

    return decorator


deprecated = t.cast(
    t.Callable[[str], t.Callable[[t.Any], t.Any]],
    getattr(warnings, "deprecated", _deprecated),
)
Method = t.Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
FuncType = t.Callable[P, R]
Decorated = t.Callable[P, R | Response]
Guard = t.Callable[[FuncType], Decorated]
