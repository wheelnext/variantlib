from __future__ import annotations

import logging
import sys
from itertools import groupby
from types import MethodType
from typing import TYPE_CHECKING
from typing import Any
from typing import get_type_hints

from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.protocols import PluginType
from variantlib.utils import classproperty
from variantlib.validators import ValidationError
from variantlib.validators import validate_type

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from typing import Callable

    from variantlib.models.variant import VariantDescription

logger = logging.getLogger(__name__)


class PluginLoader:
    """Load and query plugins"""

    _plugins: dict[str, PluginType] = {}
    _dist_names: dict[str, str] = {}

    def __new__(cls, *args: Any, **kwargs: dict[str, Any]) -> Self:
        raise RuntimeError(f"Cannot instantiate {cls.__name__}")

    @classmethod
    def flush_cache(cls) -> None:
        """Flush all loaded plugins"""
        cls._plugins = {}
        cls._dist_names = {}

    @classmethod
    def load_plugins(cls) -> None:
        """Find, load and instantiate all plugins"""

        if cls._plugins:
            return

        logger.info("Discovering Wheel Variant plugins...")
        plugins = entry_points().select(group="variantlib.plugins")

        for plugin in plugins:
            logger.info(
                "Loading plugin from entry point: %(name)s; provided by package "
                "%(package)s %(version)s",
                {
                    "name": plugin.name,
                    "package": plugin.dist.name
                    if plugin.dist is not None
                    else "unknown",
                    "version": (plugin.dist.version if plugin.dist is not None else ""),
                },
            )

            try:
                # Dynamically load the plugin class
                plugin_class = plugin.load()
            except Exception as exc:
                raise PluginError(
                    f"Loading the plugin from entry point {plugin.name} failed: {exc}"
                ) from exc

            if not callable(plugin_class):
                raise PluginError(
                    f"Entry point {plugin.name} points at a value that is not "
                    f"callable: {plugin_class!r}"
                )

            try:
                # Instantiate the plugin
                plugin_instance = plugin_class()
            except Exception as exc:
                raise PluginError(
                    f"Instantiating the plugin from entry point {plugin.name} failed: "
                    f"{exc}"
                ) from exc

            required_attributes = PluginType.__abstractmethods__
            if missing_attributes := required_attributes.difference(
                dir(plugin_instance)
            ):
                raise PluginError(
                    f"Instantiating the plugin from entry point {plugin.name} "
                    "returned an object that does not meet the PluginType prototype: "
                    f"{plugin_instance!r} (missing attributes: "
                    f"{', '.join(sorted(missing_attributes))})"
                )

            if plugin_instance.namespace in cls._plugins:
                pkg1 = cls._dist_names.get(plugin_instance.namespace)
                pkg2 = plugin.dist.name if plugin.dist is not None else None
                if pkg1 is not None and pkg2 is not None:
                    hint = f": {pkg1} or {pkg2}."
                raise RuntimeError(
                    "Two plugins found using the same namespace "
                    f"{plugin_instance.namespace}. Refusing to proceed. "
                    f"Please uninstall one of them{hint}.."
                )
            cls._plugins[plugin_instance.namespace] = plugin_instance

            if plugin.dist is not None:
                cls._dist_names[plugin_instance.namespace] = plugin.dist.name

    @classmethod
    def _call(cls, method: Callable[[], Any]) -> Any:
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

    @classmethod
    def get_supported_configs(cls) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to supported configs"""

        cls.load_plugins()
        provider_cfgs = {}
        for namespace, plugin_instance in cls._plugins.items():
            vfeat_configs = cls._call(plugin_instance.get_supported_configs)

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

    @classmethod
    def get_all_configs(cls) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to all valid configs"""

        cls.load_plugins()
        provider_cfgs = {}
        for namespace, plugin_instance in cls._plugins.items():
            vfeat_configs = cls._call(plugin_instance.get_all_configs)

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

    @classmethod
    def get_build_setup(cls, properties: VariantDescription) -> dict[str, list[str]]:
        """Get build variables for a variant made of specified properties"""
        cls.load_plugins()

        ret_env: dict[str, list[str]] = {}
        for namespace, p_props in groupby(
            sorted(properties.properties), lambda prop: prop.namespace
        ):
            if (plugin := cls._plugins.get(namespace)) is None:
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

    @classproperty
    def distribution_names(cls) -> dict[str, str]:  # noqa: N805
        """Get a mapping from plugin names to distribution names"""
        cls.load_plugins()
        return cls._dist_names

    @classproperty
    def plugins(cls) -> dict[str, PluginType]:  # noqa: N805
        """Get the loaded plugins"""
        cls.load_plugins()
        return cls._plugins

    @classproperty
    def namespaces(cls) -> list[str]:  # noqa: N805
        """Get the list of namespaces for loaded plugins"""
        return list(cls.plugins)


# cleanup - do not provide a public API for this classproperty
del classproperty
