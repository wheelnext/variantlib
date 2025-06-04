from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Generic
from typing import TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
RT = TypeVar("RT")


class VariantCache(Generic[RT]):
    """This class is not necessary today - can be used for finer cache control later."""

    cache: RT | None = None

    def __call__(self, func: Callable[[T], RT]) -> Callable[[T], RT]:
        def wrapper(*args: Any, **kwargs: dict[str, Any]) -> RT:
            if self.cache is None:
                self.cache = func(*args, **kwargs)
            return self.cache

        return wrapper
