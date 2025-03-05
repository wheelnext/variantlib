import itertools
import logging
from collections.abc import Generator

from variantlib.config import ProviderConfig
from variantlib.meta import VariantDescription
from variantlib.meta import VariantMeta

logger = logging.getLogger(__name__)


def get_combinations(data: list[ProviderConfig]) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantMeta` given a list of
    `ProviderConfig`. This function respects ordering and priority provided."""

    assert isinstance(data, (list, tuple))
    assert len(data) > 0
    assert all(isinstance(config, ProviderConfig) for config in data)

    data = [
        [
            VariantMeta(provider=provider_cnf.provider, key=key_config.key, value=val)
            for val in key_config.values  # noqa: PD011
        ]
        for provider_cnf in data
        for key_config in provider_cnf.configs
    ]

    # Generate all possible combinations, including optional elements
    for r in range(len(data), 0, -1):
        for combo in itertools.combinations(data, r):
            for vmetas in itertools.product(*combo):
                yield VariantDescription(data=vmetas)


def unpack_variants_from_json(variants_from_json: dict
                              ) -> Generator[VariantDescription]:
    def variant_to_metas(providers: dict) -> VariantMeta:
        for provider, keys in providers.items():
            for key, value in keys.items():
                yield VariantMeta(provider=provider,
                                  key=key,
                                  value=value)

    for variant_hash, providers in variants_from_json.items():
        desc = VariantDescription(variant_to_metas(providers))
        assert variant_hash == desc.hexdigest
        yield desc


def filtered_sorted_variants(variants_from_json: dict,
                             data: list[ProviderConfig]
                             ) -> Generator[VariantDescription]:
    providers = {}
    for provider_idx, provider_cnf in enumerate(data):
        keys = {}
        for key_idx, key_cnf in enumerate(provider_cnf.configs):
            keys[key_cnf.key] = key_idx, key_cnf.values
        providers[provider_cnf.provider] = provider_idx, keys

    missing_providers = set()
    missing_keys = {}

    def variant_filter(desc: VariantDescription):
        # Filter out the variant, unless all of its metas are supported.
        for meta in desc:
            if (provider_data := providers.get(meta.provider)) is None:
                missing_providers.add(meta.provider)
                return False
            _, keys = provider_data
            if (key_data := keys.get(meta.key)) is None:
                missing_keys.setdefault(meta.provider, set()).add(meta.key)
                return False
            _, values = key_data
            if meta.value not in values:
                return False
        return True

    def meta_key(meta: VariantMeta) -> tuple[int, int, int]:
        # The sort key is a tuple of (provider, key, value) indices, so that
        # the metas with more preferred (provider, key, value) sort first.
        provider_idx, keys = providers.get(meta.provider)
        key_idx, values = keys.get(meta.key)
        value_idx = values.index(meta.value)
        return provider_idx, key_idx, value_idx

    def variant_sort_key_gen(desc: VariantDescription) -> Generator[tuple]:
        # Variants with more matched values should go first.
        yield -len(desc.data)
        # Sort meta sort keys by their sort keys, so that metas containing
        # more preferred sort key sort first.
        meta_keys = sorted(meta_key(x) for x in desc.data)
        # Always prefer all values from the "stronger" keys over "weaker".
        yield from (x[0:2] for x in meta_keys)
        yield from (x[2] for x in meta_keys)

    res = sorted(filter(variant_filter,
                        unpack_variants_from_json(variants_from_json)),
                 key=lambda x: tuple(variant_sort_key_gen(x)))
    if missing_providers:
        logger.warn("No plugins provide the following variant providers: "
                    f"{' '.join(missing_providers)}; some variants will be ignored")
    for provider, provider_missing_keys in missing_keys.items():
        logger.warn(f"The {provider} provider does not provide the following expected keys: "
                    f"{' '.join(provider_missing_keys)}; some variants will be ignored")
    return res


if __name__ == "__main__":  # pragma: no cover
    import json
    from pathlib import Path

    from variantlib.config import KeyConfig

    config_custom_hw = ProviderConfig(
        provider="custom_hw",
        configs=[
            KeyConfig(key="driver_version", values=["1.3", "1.2", "1.1", "1"]),
            KeyConfig(key="hw_architecture", values=["3.4", "3"]),
        ],
    )

    config_networking = ProviderConfig(
        provider="networking",
        configs=[
            KeyConfig(key="speed", values=["10GBPS", "1GBPS", "100MBPS"]),
        ],
    )

    configs = [config_custom_hw, config_networking]

    output_f = Path("example.json")
    with output_f.open(mode="w") as outfile:
        json.dump(
            list(get_combinations(configs)),
            outfile,
            default=lambda o: o.serialize(),
            indent=4,
        )
