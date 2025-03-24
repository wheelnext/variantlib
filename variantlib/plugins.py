from __future__ import annotations

import logging
from functools import cache
from importlib.metadata import entry_points

from variantlib.config import ProviderConfig
from variantlib.metaclasses import SingletonMetaClass

logger = logging.getLogger(__name__)


class PluginLoader(metaclass=SingletonMeta):
    """Load and query plugins"""

    def __init__(self) -> None:
        self._plugins = {}
        self._dist_names = {}

        load_plugins()

    def load_plugins(self) -> None:
        """Find, load and instantiate all plugins"""

        logger.info("Discovering Wheel Variant plugins...")
        plugins = entry_points().select(group="variantlib.plugins")

        # ----------- Checking if two plugins have the same name ----------- #
        seen = set()
        duplicates = set()

        for plugin_name in [plugin.name for plugin in plugins]:
            if plugin_name in seen:
                duplicates.add(plugin_name)
            else:
                seen.add(plugin_name)

        if duplicates:
            logger.warning(
                "Duplicate plugins found: %s - Unpredicatable behavior.", duplicates
            )

        # ---------------------- Querying each plugin ---------------------- #
        for plugin in plugins:
            try:
                logger.info(f"Loading plugin: {plugin.name} - v{plugin.dist.version}")  # noqa: G004

                # Dynamically load the plugin class
                plugin_class = plugin.load()

                # Instantiate the plugin
                self._plugins[plugin.name] = plugin_class()

                # Store package distribution names for later use
                self._dist_names[plugin.name] = plugin.dist.name
            except Exception:
                logging.exception("An unknown error happened - Ignoring plugin")

    def get_provider_configs(self) -> dict[str, ProviderConfig]:
        """Get a mapping of plugin names to provider configs"""

        provider_cfgs = {}
        for name, plugin_instance in self._plugins.items():
            provider_cfg = plugin_instance.run()

            if not isinstance(provider_cfg, ProviderConfig):
                logging.error(
                    f"Provider: {name} returned an unexpected type: "  # noqa: G004
                    f"{type(provider_cfg)} - Expected: `ProviderConfig`. Ignoring..."
                )
                continue

            provider_cfgs[name] = provider_cfg

        return provider_cfgs

    def get_dist_name_mapping(self) -> dict[str, str]:
        """Get a mapping from plugin names to distribution names"""

        return self._dist_names
