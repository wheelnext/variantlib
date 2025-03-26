from __future__ import annotations

import logging
from importlib.metadata import entry_points

from variantlib.base import PluginType
from variantlib.cache import VariantCache
from variantlib.config import ProviderConfig

logger = logging.getLogger(__name__)


class classproperty(property):  # noqa: N801
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class PluginLoader:
    """Load and query plugins"""

    _plugins = {}
    _dist_names = {}

    def __new__(cls, *args, **kwargs):
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
                logging.exception("An unknown error happened - Ignoring plugin")
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
        """Get a mapping of plugin names to provider configs"""

        provider_cfgs = {}
        for namespace, plugin_instance in cls._plugins.items():
            provider_cfg = plugin_instance.get_supported_configs()

            if not isinstance(provider_cfg, ProviderConfig):
                logging.error(
                    f"Provider: {namespace} returned an unexpected type: "  # noqa: G004
                    f"{type(provider_cfg)} - Expected: `ProviderConfig`. Ignoring..."
                )
                continue

            if provider_cfg.namespace != namespace:
                logging.error(
                    "Provider %(namespace)s returned different provider namespace "
                    "in config: %(cfg_name)s. Ignoring...",
                    {"namespace": namespace, "cfg_name": provider_cfg.provider},
                )
                continue

            provider_cfgs[namespace] = provider_cfg

        return provider_cfgs

    @classproperty
    def distribution_names(cls) -> dict[str, str]:  # noqa: N805
        """Get a mapping from plugin names to distribution names"""
        return cls._dist_names

    @classproperty
    def plugins(cls) -> dict[str, str]:  # noqa: N805
        """Get the loaded plugins"""
        return cls._plugins


# cleanup - do not provide a public API for this classproperty
del classproperty
