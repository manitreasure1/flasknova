from typing import Any, Callable, TypeVar, ParamSpec
from flask.wrappers import Response


P = ParamSpec("P")
R = TypeVar("R")

GuardDecorator = Callable[[Callable[P, R]], Callable[P, R | Response]]

class FormMarker:
    def __init__(self, type_: type | None = None):
        self.type_ = type_


def Form(type_: type | None = None) -> Any:
    return FormMarker(type_)


def guard(*guards: GuardDecorator) -> Callable[[Callable[P, R]], Callable[P, R | Response]]:
    def decorator(f: Callable[P, R]) ->  Callable[P, R | Response]:
        decorated: Callable[P, R | Response] = f
        for g in reversed(guards):
            decorated = g(decorated)
        return decorated

    return decorator
