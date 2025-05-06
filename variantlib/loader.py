from __future__ import annotations

import logging
from functools import reduce
from importlib import import_module
from itertools import groupby
from types import MethodType
from typing import TYPE_CHECKING
from typing import Any
from typing import get_type_hints

from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.protocols import PluginType
from variantlib.validators import ValidationError
from variantlib.validators import validate_matches_re
from variantlib.validators import validate_type

if TYPE_CHECKING:
    from typing import Callable

    from variantlib.models.variant import VariantDescription

logger = logging.getLogger(__name__)


class PluginLoader:
    """Load and query plugins"""

    _plugins: dict[str, PluginType]

    def __init__(self) -> None:
        self._plugins = {}

    def load_plugin(self, plugin_api: str) -> None:
        """Load a specific plugin"""

        plugin_api_match = validate_matches_re(
            plugin_api, VALIDATION_PROVIDER_PLUGIN_API_REGEX
        )
        try:
            module = import_module(plugin_api_match.group("module"))
            attr_chain = plugin_api_match.group("attr").split(".")
            plugin_callable = reduce(getattr, attr_chain, module)
        except Exception as exc:
            raise PluginError(
                f"Loading the plugin from {plugin_api!r} failed: {exc}"
            ) from exc

        logger.info(
            "Loading plugin via %(plugin_api)s",
            {
                "plugin_api": plugin_api,
            },
        )

        if not callable(plugin_callable):
            raise PluginError(
                f"{plugin_api!r} points at a value that is not callable: "
                f"{plugin_callable!r}"
            )

        try:
            # Instantiate the plugin
            plugin_instance = plugin_callable()
        except Exception as exc:
            raise PluginError(
                f"Instantiating the plugin from {plugin_api!r} failed: {exc}"
            ) from exc

        required_attributes = PluginType.__abstractmethods__
        if missing_attributes := required_attributes.difference(dir(plugin_instance)):
            raise PluginError(
                f"Instantiating the plugin from {plugin_api!r} "
                "returned an object that does not meet the PluginType prototype: "
                f"{plugin_instance!r} (missing attributes: "
                f"{', '.join(sorted(missing_attributes))})"
            )

        if plugin_instance.namespace in self._plugins:
            raise RuntimeError(
                "Two plugins found using the same namespace "
                f"{plugin_instance.namespace}. Refusing to proceed."
            )

        self._plugins[plugin_instance.namespace] = plugin_instance

    def _call(self, method: Callable[[], Any]) -> Any:
        """Call plugin method and verify the return type"""

        value = method()

        try:
            validate_type(value, get_type_hints(method)["return"])
        except ValidationError as err:
            assert isinstance(method, MethodType)
            plugin_instance = method.__self__
            assert isinstance(plugin_instance, PluginType)
            raise TypeError(
                f"Provider {plugin_instance.namespace}, {method.__func__.__name__}() "
                f"method returned incorrect type. {err}"
            ) from None

        return value

    def get_supported_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to supported configs"""

        provider_cfgs = {}
        for namespace, plugin_instance in self.plugins.items():
            vfeat_configs = self._call(plugin_instance.get_supported_configs)

            # skip providers that do not return any supported configs
            if not vfeat_configs:
                continue

            provider_cfgs[namespace] = ProviderConfig(
                plugin_instance.namespace,
                configs=[
                    VariantFeatureConfig(name=vfeat_cfg.name, values=vfeat_cfg.values)
                    for vfeat_cfg in vfeat_configs
                ],
            )

        return provider_cfgs

    def get_all_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to all valid configs"""

        provider_cfgs = {}
        for namespace, plugin_instance in self.plugins.items():
            vfeat_configs = self._call(plugin_instance.get_all_configs)

            if not vfeat_configs:
                raise ValueError(
                    f"Provider {namespace}, get_all_configs() method returned no valid "
                    "configs"
                )

            provider_cfgs[namespace] = ProviderConfig(
                plugin_instance.namespace,
                configs=[
                    VariantFeatureConfig(name=vfeat_cfg.name, values=vfeat_cfg.values)
                    for vfeat_cfg in vfeat_configs
                ],
            )

        return provider_cfgs

    def get_build_setup(self, properties: VariantDescription) -> dict[str, list[str]]:
        """Get build variables for a variant made of specified properties"""

        ret_env: dict[str, list[str]] = {}
        for namespace, p_props in groupby(
            sorted(properties.properties), lambda prop: prop.namespace
        ):
            if (plugin := self.plugins.get(namespace)) is None:
                raise PluginMissingError(f"No plugin found for namespace {namespace}")

            if hasattr(plugin, "get_build_setup"):
                plugin_env = plugin.get_build_setup(list(p_props))

                try:
                    validate_type(plugin_env, dict[str, list[str]])
                except ValidationError as err:
                    raise TypeError(
                        f"Provider {namespace}, get_build_setup() "
                        f"method returned incorrect type. {err}"
                    ) from None
            else:
                plugin_env = {}

            for k, v in plugin_env.items():
                ret_env.setdefault(k, []).extend(v)
        return ret_env

    @property
    def plugins(self) -> dict[str, PluginType]:
        """Get the loaded plugins"""
        if not self._plugins:
            raise RuntimeError("No plugins loaded, use load_plugin() to load them")
        return self._plugins

    @property
    def namespaces(self) -> list[str]:
        """Get the list of namespaces for loaded plugins"""
        return list(self.plugins)
