from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Generic
from typing import TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
RT = TypeVar("RT")


class _ClassPropertyDescriptor(Generic[T, RT]):
    def __init__(self, fget: Callable[[type[T]], RT]) -> None:
        self.fget = fget

    def __get__(self, instance: T | None, owner: type[T] | None = None, /) -> RT:
        if owner is None:
            if instance is None:
                raise ValueError
            owner = type(instance)
        return self.fget(owner)


def classproperty(func: Callable[[T], RT]) -> _ClassPropertyDescriptor[T, RT]:
    return _ClassPropertyDescriptor(func)  # type: ignore[arg-type]


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


def aggregate_priority_dicts(*dicts: dict[T, list[RT]] | None) -> dict[T, list[RT]]:
    """
    Aggregate multiple priority dicts

    Takes multiple priority dicts and aggregates them into a single
    dicts, with values from the earlier dicts taking precedence
    over values from the later dicts. Dicts that are None are skipped.
    """

    result: dict[T, list[RT]] = {}
    for iter_dict in dicts:
        if iter_dict is None:
            continue
        for key, values in iter_dict.items():
            if not (ret_value := result.setdefault(key, [])):
                ret_value.extend(values)
            else:
                ret_value.extend(value for value in values if value not in ret_value)
    return result
