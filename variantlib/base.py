from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Protocol
from typing import runtime_checkable


@runtime_checkable
class KeyConfigType(Protocol):
    """A protocol for key configs"""

    key: str
    values: list[str]


@runtime_checkable
class PluginType(Protocol):
    """A protocol for plugin classes"""

    @property
    def namespace(self) -> str:
        """Get provider namespace"""
        ...

    def get_supported_configs(self) -> list[KeyConfigType]:
        """Get supported configs for the current system"""
        ...


class PluginBase(ABC):
    """An abstract base class that can be used to implement plugins"""

    @property
    @abstractmethod
    def namespace(self) -> str: ...

    @abstractmethod
    def get_supported_configs(self) -> list[KeyConfigType]: ...
