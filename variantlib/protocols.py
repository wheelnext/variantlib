# -*- coding: utf-8 -*-

# =============================================================================== #
# IMPORTANT: this file is used in variantlib/plugins/_subprocess.py
#
# This file **MUST NOT** import any other `variantlib` module.
# Must be standalone.
# =============================================================================== #

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol
from typing import runtime_checkable

# Type aliases for readability
VariantNamespace = str
VariantFeatureName = str
VariantFeatureValue = str


@runtime_checkable
class VariantFeatureConfigType(Protocol):
    """A protocol for VariantFeature configs"""

    @property
    @abstractmethod
    def name(self) -> VariantFeatureName:
        """feature name"""
        raise NotImplementedError

    @property
    @abstractmethod
    def values(self) -> list[VariantFeatureValue]:
        """Ordered list of values, most preferred first"""
        raise NotImplementedError


@runtime_checkable
class VariantPropertyType(Protocol):
    """A protocol for variant properties"""

    @property
    @abstractmethod
    def namespace(self) -> VariantNamespace:
        """Namespace (from plugin)"""
        raise NotImplementedError

    @property
    @abstractmethod
    def feature(self) -> VariantFeatureName:
        """Feature name (within the namespace)"""
        raise NotImplementedError

    @property
    @abstractmethod
    def value(self) -> VariantFeatureValue:
        """Feature value"""
        raise NotImplementedError


@runtime_checkable
class PluginStaticType(Protocol):
    """A protocol for plugin classes"""

    @property
    @abstractmethod
    def namespace(self) -> VariantNamespace:
        """Plugin namespace"""
        raise NotImplementedError

    @abstractmethod
    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        """Get all configs for the plugin"""
        raise NotImplementedError

    @abstractmethod
    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        """Get supported configs for the current system"""
        raise NotImplementedError

    def get_build_setup(
        self, properties: list[VariantPropertyType]
    ) -> dict[str, list[str]]:
        """Get build variables for a variant made of specified properties"""
        return {}


@runtime_checkable
class PluginDynamicType(Protocol):
    """A protocol for plugin classes"""

    @property
    @abstractmethod
    def namespace(self) -> VariantNamespace:
        """Plugin namespace"""
        raise NotImplementedError

    @abstractmethod
    def get_all_features(self) -> list[VariantFeatureName]:
        """Get all feature names for the plugin"""
        raise NotImplementedError

    @abstractmethod
    def filter_and_sort_properties(
        self,
        vprops: list[VariantPropertyType],
        property_priorities: list[VariantFeatureValue] | None = None,
    ) -> dict[VariantFeatureName, list[VariantFeatureValue]]:
        """Get supported properties sorted at the property level. The order of the
        `dict.keys()` is assumed to follow the prefered priority by the plugin"""
        raise NotImplementedError

    def get_build_setup(
        self, properties: list[VariantPropertyType]
    ) -> dict[str, list[str]]:
        """Get build variables for a variant made of specified properties"""
        return {}
