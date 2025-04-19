from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantProperty

if TYPE_CHECKING:
    from collections.abc import Generator


def get_combinations(
    provider_cfgs: list[ProviderConfig],
) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantProperty` given a list of
    `ProviderConfig`.

    NOTE: This function should not be assumed to respect any specific order.
    """

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
