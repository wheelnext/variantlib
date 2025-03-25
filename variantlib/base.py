from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from variantlib.config import ProviderConfig


@runtime_checkable
class PluginType(Protocol):
    """A protocol for plugin classes"""

    def get_supported_configs(self) -> ProviderConfig:
        """Get supported configs for the current system"""
        ...


class PluginBase(ABC):
    """An abstract base class that can be used to implement plugins"""

    @abstractmethod
    def get_supported_configs(self) -> ProviderConfig:
        ...
