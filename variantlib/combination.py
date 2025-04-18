from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.resolver.lib import sort_and_filter_supported_variants

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.models.provider import ProviderConfig

logger = logging.getLogger(__name__)


def unpack_variants_from_json(
    variants_from_json: dict,
) -> Generator[VariantDescription]:
    def variant_to_vprops(namespaces: dict) -> Generator[VariantProperty]:
        for namespace, keys in namespaces.items():
            for key, value in keys.items():
                yield VariantProperty(namespace=namespace, feature=key, value=value)

    for vhash, namespaces in variants_from_json.items():
        vdesc = VariantDescription(list(variant_to_vprops(namespaces)))
        assert vhash == vdesc.hexdigest
        yield vdesc


def filtered_sorted_variants(
    variants_from_json: dict, provider_configs: list[ProviderConfig]
) -> list[VariantDescription]:
    vdescs = list(unpack_variants_from_json(variants_from_json))
    supported_vprops = list(
        itertools.chain.from_iterable(
            provider_cfg.to_list_of_properties() for provider_cfg in provider_configs
        )
    )
    return sort_and_filter_supported_variants(
        vdescs,
        supported_vprops,
        namespace_priorities=[x.namespace for x in provider_configs],
    )
