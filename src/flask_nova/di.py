from __future__ import annotations

import typing as t

T = t.TypeVar("T")


class Depend(t.Generic[T]):
    def __init__(self, dependency: t.Callable[..., T]) -> None:
        self.dependency = dependency

    def __getitem__(self, key) -> None:
        pass
