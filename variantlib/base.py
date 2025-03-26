from abc import ABC
from abc import abstractmethod
from typing import Protocol
from typing import runtime_checkable

from variantlib.config import ProviderConfig


@runtime_checkable
class PluginType(Protocol):
    """A protocol for plugin classes"""

    @property
    def namespace(self) -> str:
        """Get provider namespace"""
        ...

    def get_supported_configs(self) -> ProviderConfig:
        """Get supported configs for the current system"""
        ...


class PluginBase(ABC):
    """An abstract base class that can be used to implement plugins"""

    @property
    @abstractmethod
    def namespace(self) -> str: ...

    @abstractmethod
    def get_supported_configs(self) -> ProviderConfig: ...
