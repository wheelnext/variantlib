import itertools
from collections.abc import Generator

from variantlib.config import ProviderConfig
from variantlib.meta import VariantDescription
from variantlib.meta import VariantMeta


def get_combinations(data: list[ProviderConfig]) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantMeta` given a list of
    `ProviderConfig`. This function respects ordering and priority provided."""

    assert isinstance(data, (list, tuple))
    assert len(data) > 0
    assert all(isinstance(config, ProviderConfig) for config in data)

    data = [
        [
            VariantMeta(provider=provider_cnf.provider, key=key_config.key, value=val)
            for val in key_config.values
        ]
        for provider_cnf in data
        for key_config in provider_cnf.configs
    ]

    # Generate all possible combinations, including optional elements
    for r in range(len(data), 0, -1):
        for combo in itertools.combinations(data, r):
            for vmetas in itertools.product(*combo):
                yield VariantDescription(data=list(vmetas))


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
