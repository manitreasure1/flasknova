from __future__ import annotations

import typing as t
from .typed import (
    Guard,
    Decorated,
    FileMarker,
    FormMarker,
    FuncType,
)


def guard(
    *guards: Guard,
) -> Guard:
    def decorator(f: FuncType) -> Decorated:
        decorated: Decorated = f
        for g in reversed(guards):
            decorated = g(decorated)
        return decorated

    return decorator


def Form(type_: type | None = None) -> t.Any:
    return FormMarker(type_)


def File(name: str, multiple: bool = False) -> t.Any:
    return FileMarker(name, multiple)
