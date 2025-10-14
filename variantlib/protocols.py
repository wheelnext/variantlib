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
    def multi_value(self) -> bool:
        """Does this property allow multiple values per variant?"""
        raise NotImplementedError

    @property
    @abstractmethod
    def values(self) -> list[VariantFeatureValue]:
        """Ordered list of values, most preferred first"""
        raise NotImplementedError


@runtime_checkable
class PluginType(Protocol):
    """A protocol for plugin classes"""

    # Note: properties are used here for docstring purposes, these must
    # be actually implemented as attributes.

    @property
    @abstractmethod
    def namespace(self) -> VariantNamespace:
        """Plugin namespace"""
        raise NotImplementedError

    @property
    def is_aot_plugin(self) -> bool:
        """
        Is this plugin valid for use with `install-time = false`?

        If this is True, then `get_supported_configs()` must always
        return the same values, irrespective of the platform used.
        This permits the plugin to be used with `install-time = false`,
        where the supported properties are recorded at build time.

        If the value of `get_supported_configs()` may change in any way
        depending on the platform used, then it must be False
        (the default).
        """
        return False

    @classmethod
    @abstractmethod
    def get_all_configs(cls) -> list[VariantFeatureConfigType]:
        """Get all valid configs for the plugin"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_supported_configs(cls) -> list[VariantFeatureConfigType]:
        """Get supported configs for the current system"""
        raise NotImplementedError
