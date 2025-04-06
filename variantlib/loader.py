from __future__ import annotations

import logging
import sys
from importlib.metadata import entry_points
from typing import Any

from variantlib.base import PluginType
from variantlib.base import VariantFeatureConfigType
from variantlib.cache import VariantCache
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.utils import classproperty

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

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

        logger.info("Discovering Wheel Variant plugins...")
        plugins = entry_points().select(group="variantlib.plugins")

        for plugin in plugins:
            try:
                logger.info(
                    "Loading plugin: %(name)s - version %(version)s",
                    {
                        "name": plugin.name,
                        "version": (
                            plugin.dist.version
                            if plugin.dist is not None
                            else "unknown"
                        ),
                    },
                )

                # Dynamically load the plugin class
                plugin_class = plugin.load()

                # Instantiate the plugin
                plugin_instance = plugin_class()
                assert isinstance(plugin_instance, PluginType)

            except Exception:  # noqa: PERF203
                logger.exception("An unknown error happened - Ignoring plugin")
                continue

            else:
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
    @VariantCache()
    def get_supported_configs(cls) -> dict[str, ProviderConfig]:
        """Get a mapping of namespaces to supported configs"""

        provider_cfgs = {}
        for namespace, plugin_instance in cls._plugins.items():
            vfeat_configs = plugin_instance.get_supported_configs()

            if not isinstance(vfeat_configs, list):
                logging.error(
                    "Provider: %(namespace)s returned an unexpected type: "
                    "%(type)s - Expected: `list[VariantFeatureConfig]`. Ignoring...",
                    {"namespace": namespace, "type": type(vfeat_configs)},
                )
                continue

            # skip providers that do not return any supported configs
            if not vfeat_configs:
                continue

            for vfeat_cfg in vfeat_configs:
                if not isinstance(vfeat_cfg, VariantFeatureConfigType):
                    logging.error(
                        "Provider: %(namespace)s returned an unexpected list member "
                        "type: %(type)s - Expected: `VariantFeatureConfigType`. "
                        "Ignoring...",
                        {"namespace": namespace, "type": type(vfeat_configs)},
                    )
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

        provider_cfgs = {}
        for namespace, plugin_instance in cls._plugins.items():
            key_configs = plugin_instance.get_all_configs()

            if not isinstance(key_configs, list):
                raise TypeError(
                    f"Provider {namespace}, get_all_configs() method returned "
                    f"incorrect type {type(key_configs)}, excepted: "
                    "list[VariantFeatureConfig]"
                )

            if not key_configs:
                raise ValueError(
                    f"Provider {namespace}, get_all_configs() method returned no valid "
                    "configs"
                )

            for vfeat_cfg in key_configs:
                if not isinstance(vfeat_cfg, VariantFeatureConfigType):
                    raise TypeError(
                        f"Provider {namespace}, get_all_configs() method returned "
                        f"incorrect list member type {type(vfeat_cfg)}, excepted: "
                        "VariantFeatureConfig"
                    )

            provider_cfgs[namespace] = ProviderConfig(
                plugin_instance.namespace,
                configs=[
                    VariantFeatureConfig(name=vfeat_cfg.name, values=vfeat_cfg.values)
                    for vfeat_cfg in key_configs
                ],
            )

        return provider_cfgs

    @classproperty
    def distribution_names(cls) -> dict[str, str]:  # noqa: N805
        """Get a mapping from plugin names to distribution names"""
        return cls._dist_names

    @classproperty
    def plugins(cls) -> dict[str, PluginType]:  # noqa: N805
        """Get the loaded plugins"""
        return cls._plugins


# cleanup - do not provide a public API for this classproperty
del classproperty
