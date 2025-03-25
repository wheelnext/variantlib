from typing import Protocol, runtime_checkable

from variantlib.config import ProviderConfig


@runtime_checkable
class PluginType(Protocol):
    """A protocol for plugin classes"""

    def get_supported_configs(self) -> ProviderConfig:
        """Get supported configs for the current system"""
        ...
