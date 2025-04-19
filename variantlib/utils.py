from __future__ import annotations

from typing import Any
from typing import TypeVar


class classproperty(property):  # noqa: N801
    def __get__(self, cls: Any, owner: type | None = None) -> Any:
        return classmethod(self.fget).__get__(None, owner)()  # type: ignore[arg-type]


T = TypeVar("T")


def aggregate_user_and_default_lists(
    user_list: list[T] | None, default_list: list[T]
) -> list[T]:
    """
    Aggregate a user-provided list with a default list.

    If the user-provided list is None, return the default list.
    Otherwise, return the user-provided list.
    """
    if user_list is None:
        return default_list

    for item in default_list:
        if item not in user_list:
            user_list.append(item)
    return user_list
