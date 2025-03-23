from __future__ import annotations

import logging
from collections import defaultdict
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from variantlib.combination import filtered_sorted_variants
from variantlib.combination import get_combinations
from variantlib.config import ProviderConfig

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.meta import VariantDescription

logger = logging.getLogger(__name__)


class VariantCache:
    """This class is not necessary today - can be used for finer cache control later."""

    def __init__(self):
        self.cache = None

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            if self.cache is None:
                self.cache = func(*args, **kwargs)
            return self.cache

        return wrapper


@VariantCache()
def _query_variant_plugins() -> dict[str, ProviderConfig]:
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
    provider_cfgs = {}
    for plugin in plugins:
        try:
            logger.info(f"Loading plugin: {plugin.name} - v{plugin.dist.version}")  # noqa: G004

            # Dynamically load the plugin class
            plugin_class = plugin.load()

            # Instantiate the plugin
            plugin_instance = plugin_class()

            # Call the `run` method of the plugin
            provider_cfg = plugin_instance.run()

            if not isinstance(provider_cfg, ProviderConfig):
                logging.error(
                    f"Provider: {plugin.name} returned an unexpected type: "  # noqa: G004
                    f"{type(provider_cfg)} - Expected: `ProviderConfig`. Ignoring..."
                )
                continue

            provider_cfgs[plugin.name] = provider_cfg

        except Exception:
            logging.exception("An unknown error happened - Ignoring plugin")

    return provider_cfgs


def get_variant_hashes_by_priority(
    provider_priority_dict: dict[str:int] | None = None,
    variants_json: dict | None = None,
) -> Generator[VariantDescription]:
    plugins = entry_points().select(group="variantlib.plugins")

    # sorting providers in priority order:
    if provider_priority_dict is not None:
        if (
            not isinstance(provider_priority_dict, dict)
            or not all(isinstance(key, str) for key in provider_priority_dict)
            or not all(isinstance(key, int) for key in provider_priority_dict.values())
        ):
            logger.warning(
                "Invalid `provider_priority_dict` provided. Should follow "
                "format: dict[str:int]. Ignoring..."
            )
        else:
            # ----------- Checking if two plugins hold the same priority ----------- #
            value_to_keys = defaultdict(list)  # temp storage

            # Populate the dictionary with values and their corresponding keys
            for key, value in provider_priority_dict.items():
                value_to_keys[value].append(key)

            # Isolate the duplicate values and their corresponding keys
            duplicates = {
                value: keys for value, keys in value_to_keys.items() if len(keys) > 1
            }

            if duplicates:
                logger.warning("Duplicate values and their corresponding keys:")
                for value, keys in duplicates.items():
                    logger.warning("Value: %s -> Keys: %s", value, keys)

            # ----------- Checking if two plugins hold the same priority ----------- #
            for plugin in plugins:
                if plugin.name not in provider_priority_dict:
                    logger.warning(
                        "Plugin: %s is not present in the `provider_priority_dict`. "
                        "Will be treated as lowest priority.",
                        plugin.name,
                    )
                    continue

            # ------------------- Sorting the plugins by priority ------------------ #
            plugins = sorted(
                plugins,
                key=lambda plg: provider_priority_dict.get(plg.name, float("inf")),
            )

    provider_cfgs = _query_variant_plugins()
    sorted_provider_cfgs = [provider_cfgs[plugin.name] for plugin in plugins]

    if sorted_provider_cfgs:
        if (variants_json or {}).get("variants") is not None:
            for variant_desc in filtered_sorted_variants(
                variants_json["variants"], sorted_provider_cfgs
            ):
                yield variant_desc.hexdigest
        else:
            for variant_desc in get_combinations(sorted_provider_cfgs):
                yield variant_desc.hexdigest
    else:
        yield from []
