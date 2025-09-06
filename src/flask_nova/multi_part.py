from typing import Any, Callable



class FormMarker:
    def __init__(self, type_: type | None = None):
        self.type_ = type_

def Form(type_: type | None = None)->Any:
    return FormMarker(type_)


def guard(*guards: Callable[[Callable], Callable]):
    def decorator(f: Callable) -> Callable:
        for g in reversed(guards):
            f = g(f)
        return f
    return decorator

