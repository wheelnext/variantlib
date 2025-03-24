from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

from variantlib.combination import filtered_sorted_variants
from variantlib.combination import get_combinations
from variantlib.plugins import PluginLoader

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.config import ProviderConfig
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
    return PluginLoader().get_supported_configs()


def get_variant_hashes_by_priority(
    provider_priority_dict: Optional[dict[str:int]] = None,
    variants_json: Optional[dict] = None,
) -> Generator[VariantDescription]:
    provider_cfgs = _query_variant_plugins()

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
            for plugin_name in provider_cfgs:
                if plugin_name not in provider_priority_dict:
                    logger.warning(
                        "Plugin: %s is not present in the `provider_priority_dict`. "
                        "Will be treated as lowest priority.",
                        plugin_name,
                    )
                    continue

            # ------------------- Sorting the plugins by priority ------------------ #
            plugins = sorted(
                provider_cfgs,
                key=lambda plugin_name: provider_priority_dict.get(
                    plugin_name, float("inf")
                ),
            )

            sorted_provider_cfgs = [
                provider_cfgs[plugin_name] for plugin_name in plugins
            ]
    else:
        sorted_provider_cfgs = list(provider_cfgs.values())

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
