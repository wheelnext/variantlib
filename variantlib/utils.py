from __future__ import annotations

from typing import Any


class classproperty(property):  # noqa: N801
    def __get__(self, cls: Any, owner: type | None = None) -> Any:
        return classmethod(self.fget).__get__(None, owner)()  # type: ignore[arg-type]
