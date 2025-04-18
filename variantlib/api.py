"""This file regroups the public API of the variantlib package."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

from variantlib.constants import METADATA_VARIANT_HASH_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_HEADER
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.loader import PluginLoader
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.models.variant import VariantValidationResult
from variantlib.resolver.lib import sort_and_filter_supported_variants

if TYPE_CHECKING:
    from collections.abc import Generator
    from email.message import Message

logger = logging.getLogger(__name__)

__all__ = [
    "VARIANT_HASH_LEN",
    "ProviderConfig",
    "VariantDescription",
    "VariantFeatureConfig",
    "VariantProperty",
    "get_variant_hashes_by_priority",
    "set_variant_metadata",
    "validate_variant",
]


def _unpack_variants_json(
    variants_json: dict,
) -> Generator[VariantDescription]:
    def variant_to_vprops(namespaces: dict) -> Generator[VariantProperty]:
        for namespace, keys in namespaces.items():
            for key, value in keys.items():
                yield VariantProperty(namespace=namespace, feature=key, value=value)

    for vhash, namespaces in variants_json["variants"].items():
        vdesc = VariantDescription(list(variant_to_vprops(namespaces)))
        assert vhash == vdesc.hexdigest
        yield vdesc


def get_variant_hashes_by_priority(
    *,
    variants_json: dict,
) -> Generator[str]:
    provider_configs = list(PluginLoader.get_supported_configs().values())
    vdescs = list(_unpack_variants_json(variants_json))
    supported_vprops = list(
        itertools.chain.from_iterable(
            provider_cfg.to_list_of_properties() for provider_cfg in provider_configs
        )
    )

    for vdesc in sort_and_filter_supported_variants(
        vdescs,
        supported_vprops,
        namespace_priorities=[x.namespace for x in provider_configs],
    ):
        yield vdesc.hexdigest


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


def set_variant_metadata(
    metadata: Message,
    vdesc: VariantDescription,
) -> None:
    """Set metadata-related keys in metadata email-dict"""

    # Match namespaces to plugins
    namespaces = {vprop.namespace for vprop in vdesc.properties}
    providers = {ns: PluginLoader.distribution_names[ns] for ns in namespaces}

    # Remove old metadata
    del metadata[METADATA_VARIANT_PROPERTY_HEADER]
    del metadata[METADATA_VARIANT_HASH_HEADER]
    del metadata[METADATA_VARIANT_PROVIDER_HEADER]

    # Add new metadata
    for vprop in vdesc.properties:
        metadata[METADATA_VARIANT_PROPERTY_HEADER] = vprop.to_str()
    metadata[METADATA_VARIANT_HASH_HEADER] = vdesc.hexdigest
    for ns, provider in sorted(providers.items()):
        # Follow the "<key>, <value>" format used in metadata already:
        # https://packaging.python.org/en/latest/specifications/core-metadata/#project-url-multiple-use
        metadata[METADATA_VARIANT_PROVIDER_HEADER] = f"{ns}, {provider}"
