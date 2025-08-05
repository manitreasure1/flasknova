from typing import Callable

class Form:
    """
    Describes a form field submitted via multipart/form-data or application/x-www-form-urlencoded.
    Used with Annotated:
        username: Annotated[str, Form()]
    """

def guard(*guards: Callable[[Callable], Callable]):
    def decorator(f: Callable) -> Callable:
        for g in reversed(guards):
            f = g(f)
        return f
    return decorator

