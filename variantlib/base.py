from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Protocol
from typing import runtime_checkable

if TYPE_CHECKING:
    from variantlib.config import KeyConfig


@runtime_checkable
class PluginType(Protocol):
    """A protocol for plugin classes"""

    @property
    def namespace(self) -> str:
        """Get provider namespace"""
        ...

    def get_supported_configs(self) -> list[KeyConfig]:
        """Get supported configs for the current system"""
        ...


class PluginBase(ABC):
    """An abstract base class that can be used to implement plugins"""

    @property
    @abstractmethod
    def namespace(self) -> str: ...

    @abstractmethod
    def get_supported_configs(self) -> list[KeyConfig]: ...
