from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class VariantCache(Generic[T]):
    """This class is not necessary today - can be used for finer cache control later."""

    def __init__(self) -> None:
        self.cache: T | None = None

    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: dict[str, Any]) -> T:
            if self.cache is None:
                self.cache = func(*args, **kwargs)
            return self.cache

        return wrapper
