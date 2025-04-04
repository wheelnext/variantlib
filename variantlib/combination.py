from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

from variantlib.models.provider import ProviderConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)


def get_combinations(
    provider_cfgs: list[ProviderConfig],
) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantProperty` given a list of
    `ProviderConfig`. This function respects ordering and priority provided."""

    assert isinstance(provider_cfgs, (list, tuple))
    assert len(provider_cfgs) > 0
    assert all(isinstance(config, ProviderConfig) for config in provider_cfgs)

    vprop_lists = [
        [
            VariantProperty(
                namespace=provider_cfg.namespace,
                feature=vfeat_config.name,
                value=vprop_value,
            )
            for vprop_value in vfeat_config.values
        ]
        for provider_cfg in provider_cfgs
        for vfeat_config in provider_cfg.configs
    ]

    # Generate all possible combinations, including optional elements
    for r in range(len(vprop_lists), 0, -1):
        for combo in itertools.combinations(vprop_lists, r):
            for vprops in itertools.product(*combo):
                yield VariantDescription(properties=list(vprops))


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


def filtered_sorted_variants(  # noqa: C901
    variants_from_json: dict, provider_configs: list[ProviderConfig]
) -> list[VariantDescription]:
    namespaces = {}
    for namespace_idx, namespace_cnf in enumerate(provider_configs):
        keys = {}
        for key_idx, key_cnf in enumerate(namespace_cnf.configs):
            keys[key_cnf.name] = key_idx, key_cnf.values
        namespaces[namespace_cnf.namespace] = namespace_idx, keys

    missing_namespaces = set()
    missing_keys: dict[str, set[str]] = {}

    def variant_filter(vdesc: VariantDescription) -> bool:
        # Filter out the variant, unless all of its vprops are supported.
        for vprop in vdesc.properties:
            if (namespace_data := namespaces.get(vprop.namespace)) is None:
                missing_namespaces.add(vprop.namespace)
                return False
            _, keys = namespace_data
            if (key_data := keys.get(vprop.feature)) is None:
                missing_keys.setdefault(vprop.namespace, set()).add(vprop.feature)
                return False
            _, values = key_data
            if vprop.value not in values:
                return False
        return True

    def vprop_key(vprop: VariantProperty) -> tuple[int, int, int]:
        # The sort key is a tuple of (namespace, key, value) indices, so that
        # the vprops with more preferred (namespace, key, value) sort first.
        namespace_idx, keys = namespaces[vprop.namespace]
        key_idx, values = keys[vprop.feature]
        value_idx = values.index(vprop.value)
        return namespace_idx, key_idx, value_idx

    def variant_sort_key_gen(
        vdesc: VariantDescription,
    ) -> Generator[int | tuple[int, int]]:
        # Variants with more matched values should go first.
        yield -len(vdesc.properties)
        # Sort vprop by their sort keys, so that vprops containing
        # more preferred sort key sort first.
        vprop_keys = sorted(vprop_key(x) for x in vdesc.properties)
        # Always prefer all values from the "stronger" keys over "weaker".
        yield from (x[0:2] for x in vprop_keys)
        yield from (x[2] for x in vprop_keys)

    res = sorted(
        filter(variant_filter, unpack_variants_from_json(variants_from_json)),
        key=lambda x: tuple(variant_sort_key_gen(x)),
    )

    if missing_namespaces:
        logger.warning(
            "No plugins provide the following variant namespaces: "
            "%(namespace)s; some variants will be ignored",
            {"namespace": " ".join(missing_namespaces)},
        )

    for namespace, namespace_missing_keys in missing_keys.items():
        logger.warning(
            "The %(namespace)s provider does not provide the following expected keys: "
            "%(missing_keys)s; some variants will be ignored",
            {"namespace": namespace, "missing_keys": " ".join(namespace_missing_keys)},
        )

    return res
