# -*- coding: utf-8 -*-

# =============================================================================== #
# IMPORTANT: this file is used in variantlib/plugins/_subprocess.py
#
# This file **MUST NOT** import any other `variantlib` module.
# Must be standalone.
# =============================================================================== #

"""
Protocols for the plugin API

This file provides a number of protocols outlining the design of the plugin API.
The classes serve a dual purpose: they are meant to help plugin authors
visualize the plugin API, and they can also serve as abstract base classes
for an actual plugin implementation. This module is intended to be fully
self-contained and standalone, and it can be easily vendored into a plugin.

The central class is PluginType, which defined the API provided by the plugin.
The actual API can be implemented as regular methods on a class (optionally
subclassing PluginType), class methods, static methods or top-level functions
in a module.

The methods declared as abstract here must be defined by the plugin.
The remaining methods are optional. If they are not defined, the caller
assumes a default value equivalent to the implementation provided in the class.
This means that plugins do not need to define them even if they do not subclass
the protocol classes.
"""

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
class PluginType(Protocol):
    """A protocol for plugin classes"""

    @property
    @abstractmethod
    def namespace(self) -> VariantNamespace:
        """Plugin namespace"""
        raise NotImplementedError

    @property
    @abstractmethod
    def dynamic(self) -> bool:
        """
        Is this a dynamic plugin?

        This property / attribute should return True if the configs
        returned `get_supported_configs()` depend on `known_properties`
        input.  If it is False, `known_properties` will be `None`.
        """
        raise NotImplementedError

    @abstractmethod
    def get_supported_configs(
        self, known_properties: frozenset[VariantPropertyType] | None
    ) -> list[VariantFeatureConfigType]:
        """Get supported configs for the current system"""
        raise NotImplementedError

    @abstractmethod
    def validate_property(self, variant_property: VariantPropertyType) -> bool:
        """Validate variant property, returns True if it's valid"""
        raise NotImplementedError
