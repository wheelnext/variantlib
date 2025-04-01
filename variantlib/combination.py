from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

from variantlib.models.provider import ProviderConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantMetadata

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)


def get_combinations(data: list[ProviderConfig]) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantMetadata` given a list of
    `ProviderConfig`. This function respects ordering and priority provided."""

    assert isinstance(data, (list, tuple))
    assert len(data) > 0
    assert all(isinstance(config, ProviderConfig) for config in data)

    meta_lists = [
        [
            VariantMetadata(
                namespace=provider_cnf.namespace, key=vfeat_cfg.name, value=val
            )
            for val in vfeat_cfg.values
        ]
        for provider_cnf in data
        for vfeat_cfg in provider_cnf.configs
    ]

    # Generate all possible combinations, including optional elements
    for r in range(len(meta_lists), 0, -1):
        for combo in itertools.combinations(meta_lists, r):
            for vmetas in itertools.product(*combo):
                yield VariantDescription(data=list(vmetas))


def unpack_variants_from_json(
    variants_from_json: dict,
) -> Generator[VariantDescription]:
    def variant_to_metas(namespaces: dict) -> Generator[VariantMetadata]:
        for namespace, keys in namespaces.items():
            for key, value in keys.items():
                yield VariantMetadata(namespace=namespace, key=key, value=value)

    for variant_hash, namespaces in variants_from_json.items():
        desc = VariantDescription(list(variant_to_metas(namespaces)))
        assert variant_hash == desc.hexdigest
        yield desc


def filtered_sorted_variants(  # noqa: C901
    variants_from_json: dict, data: list[ProviderConfig]
) -> list[VariantDescription]:
    namespaces = {}
    for namespace_idx, namespace_cnf in enumerate(data):
        keys = {}
        for key_idx, key_cnf in enumerate(namespace_cnf.configs):
            keys[key_cnf.name] = key_idx, key_cnf.values
        namespaces[namespace_cnf.namespace] = namespace_idx, keys

    missing_namespaces = set()
    missing_keys: dict[str, set[str]] = {}

    def variant_filter(desc: VariantDescription) -> bool:
        # Filter out the variant, unless all of its metas are supported.
        for meta in desc:
            if (namespace_data := namespaces.get(meta.namespace)) is None:
                missing_namespaces.add(meta.namespace)
                return False
            _, keys = namespace_data
            if (key_data := keys.get(meta.key)) is None:
                missing_keys.setdefault(meta.namespace, set()).add(meta.key)
                return False
            _, values = key_data
            if meta.value not in values:
                return False
        return True

    def meta_key(meta: VariantMetadata) -> tuple[int, int, int]:
        # The sort key is a tuple of (namespace, key, value) indices, so that
        # the metas with more preferred (namespace, key, value) sort first.
        namespace_idx, keys = namespaces[meta.namespace]
        key_idx, values = keys[meta.key]
        value_idx = values.index(meta.value)
        return namespace_idx, key_idx, value_idx

    def variant_sort_key_gen(
        desc: VariantDescription,
    ) -> Generator[int | tuple[int, int]]:
        # Variants with more matched values should go first.
        yield -len(desc.data)
        # Sort meta sort keys by their sort keys, so that metas containing
        # more preferred sort key sort first.
        meta_keys = sorted(meta_key(x) for x in desc.data)
        # Always prefer all values from the "stronger" keys over "weaker".
        yield from (x[0:2] for x in meta_keys)
        yield from (x[2] for x in meta_keys)

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
