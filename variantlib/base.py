from __future__ import annotations

from abc import abstractmethod
from typing import Protocol
from typing import runtime_checkable


@runtime_checkable
class VariantFeatureConfigType(Protocol):
    """A protocol for VariantFeature configs"""

    @property
    def name(self) -> str:
        """feature name"""
        ...

    @property
    def values(self) -> list[str]:
        """Ordered list of values, most preferred first"""
        ...


@runtime_checkable
class PluginType(Protocol):
    """A protocol for plugin classes"""

    @property
    @abstractmethod
    def namespace(self) -> str:
        """Get provider namespace"""
        raise NotImplementedError

    @abstractmethod
    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        """Get all configs for the plugin"""
        raise NotImplementedError

    @abstractmethod
    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        """Get supported configs for the current system"""
        raise NotImplementedError
