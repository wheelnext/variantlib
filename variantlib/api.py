"""This file regroups the public API of the variantlib package."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from variantlib.combination import filtered_sorted_variants
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.loader import PluginLoader
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)

__all__ = [
    "VARIANT_HASH_LEN",
    "ProviderConfig",
    "VariantDescription",
    "VariantFeatureConfig",
    "VariantProperty",
    "get_variant_hashes_by_priority",
    "validate_variant",
]


def get_variant_hashes_by_priority(
    *,
    variants_json: dict,
    namespace_priority_dict: dict[str, int] | None = None,
) -> Generator[str]:
    provider_cfgs = PluginLoader.get_supported_configs()

    # sorting providers in priority order:
    if namespace_priority_dict is not None:
        if (
            not isinstance(namespace_priority_dict, dict)
            or not all(isinstance(key, str) for key in namespace_priority_dict)
            or not all(isinstance(key, int) for key in namespace_priority_dict.values())
        ):
            logger.warning(
                "Invalid `namespace_priority_dict` provided. Should follow "
                "format: dict[str:int]. Ignoring..."
            )
        else:
            # ----------- Checking if two plugins hold the same priority ----------- #
            value_to_keys = defaultdict(list)  # temp storage

            # Populate the dictionary with values and their corresponding keys
            for key, value in namespace_priority_dict.items():
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
            for namespace in provider_cfgs:
                if namespace not in namespace_priority_dict:
                    logger.warning(
                        "Plugin: %s is not present in the `namespace_priority_dict`. "
                        "Will be treated as lowest priority.",
                        namespace,
                    )
                    continue

            # ------------------- Sorting the plugins by priority ------------------ #
            plugins = sorted(
                provider_cfgs,
                key=lambda namespace: namespace_priority_dict.get(
                    namespace, float("inf")
                ),
            )

            sorted_provider_cfgs = [provider_cfgs[namespace] for namespace in plugins]
    else:
        sorted_provider_cfgs = list(provider_cfgs.values())

    if sorted_provider_cfgs:
        for vdesc in filtered_sorted_variants(
            variants_json["variants"], sorted_provider_cfgs
        ):
            yield vdesc.hexdigest
    else:
        yield from []


@dataclass
class VariantValidationResult:
    results: dict[VariantProperty, bool | None]

    def is_valid(self, allow_unknown_plugins: bool = True) -> bool:
        return False not in self.results.values() and (
            allow_unknown_plugins or None not in self.results.values()
        )


def validate_variant(
    variant_desc: VariantDescription,
) -> VariantValidationResult:
    """
    Validate all metas in the variant description

    Check whether all metas in the variant description are valid, and return
    a dictionary mapping individual metas into a tri-state variable: True
    indicates that the variant is valid, False that it is not, and None
    that no plugin provides given namespace and therefore the variant cannot
    be verified.
    """

    provider_cfgs = PluginLoader.get_all_configs()

    def _validate_variant(vprop: VariantProperty) -> bool | None:
        provider_cfg = provider_cfgs.get(vprop.namespace)
        if provider_cfg is None:
            return None
        for key_cfg in provider_cfg.configs:
            if key_cfg.name == vprop.feature:
                return vprop.value in key_cfg.values
        return False

    return VariantValidationResult(
        {vprop: _validate_variant(vprop) for vprop in variant_desc.properties}
    )
