from __future__ import annotations

from typing import Any
from typing import TypeVar


class classproperty(property):  # noqa: N801
    def __get__(self, cls: Any, owner: type | None = None) -> Any:
        return classmethod(self.fget).__get__(None, owner)()  # type: ignore[arg-type]


T = TypeVar("T")


def aggregate_priority_lists(*lists: list[T] | None) -> list[T]:
    """
    Aggregate multiple priority lists

    Takes multiple priority lists and aggregates them into a single
    list, with items from the earlier lists taking precedence over items
    from the later lists. Lists that are None are skipped.
    """

    result: list[T] = []
    for iter_list in lists:
        if iter_list is None:
            continue
        if not result:
            result.extend(iter_list)
        else:
            result.extend(item for item in iter_list if item not in result)
    return result
