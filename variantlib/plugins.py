from __future__ import annotations

import logging
from importlib.metadata import entry_points

from variantlib.base import PluginType
from variantlib.config import ProviderConfig
from variantlib.metaclasses import SingletonMetaClass

logger = logging.getLogger(__name__)


class PluginLoader(metaclass=SingletonMetaClass):
    """Load and query plugins"""

    def __init__(self) -> None:
        self._plugins = {}
        self._dist_names = {}
        self.load_plugins()

    def load_plugins(self) -> None:
        """Find, load and instantiate all plugins"""

        logger.info("Discovering Wheel Variant plugins...")
        plugins = entry_points().select(group="variantlib.plugins")
        duplicates = set()

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
            except Exception:
                logging.exception("An unknown error happened - Ignoring plugin")
            else:
                if plugin_instance.name in self._plugins:
                    duplicates.add(plugin_instance.name)
                self._plugins[plugin_instance.name] = plugin_instance

                if plugin.dist is not None:
                    self._dist_names[plugin_instance.name] = plugin.dist.name

        if duplicates:
            logger.warning(
                "Duplicate plugins found: %s - Unpredicatable behavior.", duplicates
            )

    def get_supported_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of plugin names to provider configs"""

        provider_cfgs = {}
        for name, plugin_instance in self._plugins.items():
            provider_cfg = plugin_instance.get_supported_configs()

            if not isinstance(provider_cfg, ProviderConfig):
                logging.error(
                    f"Provider: {name} returned an unexpected type: "  # noqa: G004
                    f"{type(provider_cfg)} - Expected: `ProviderConfig`. Ignoring..."
                )
                continue

            if provider_cfg.provider != name:
                logging.error(
                    "Provider %(name)s returned different provider name "
                    "in config: %(cfg_name)s. Ignoring...",
                    {"name": name, "cfg_name": provider_cfg.provider},
                )
                continue

            provider_cfgs[name] = provider_cfg

        return provider_cfgs

    def get_dist_name_mapping(self) -> dict[str, str]:
        """Get a mapping from plugin names to distribution names"""

        return self._dist_names
