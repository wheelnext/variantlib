from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.validators import validate_type

if TYPE_CHECKING:
    from collections.abc import Generator


def get_combinations(
    provider_cfgs: list[ProviderConfig], namespace_priorities: list[str]
) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantProperty` given a list of
    `ProviderConfig`.

    NOTE: This function respects some basic ordering and priority."""

    assert isinstance(provider_cfgs, (list, tuple))
    assert len(provider_cfgs) > 0
    assert all(isinstance(config, ProviderConfig) for config in provider_cfgs)

    validate_type(provider_cfgs, list[ProviderConfig])
    validate_type(namespace_priorities, list[str])

    provider_cfgs_dict = {
        provider_cfg.namespace: provider_cfg for provider_cfg in provider_cfgs
    }

    all_properties = [
        (provider_cfgs_dict[namespace].namespace, feature_cfg.name, feature_cfg.values)
        for namespace in namespace_priorities
        for feature_cfg in provider_cfgs_dict[namespace].configs
        if namespace in provider_cfgs_dict
    ]

    def yield_all_values(
        remaining_properties: list[tuple[str, str, list[str]]],
    ) -> Generator[list[VariantProperty]]:
        namespace, feature, values = remaining_properties[0]
        for value in values:
            for start in range(1, len(remaining_properties)):
                for other_values in yield_all_values(remaining_properties[start:]):
                    yield [VariantProperty(namespace, feature, value), *other_values]
            yield [VariantProperty(namespace, feature, value)]

    for start in range(len(all_properties)):
        for properties in yield_all_values(all_properties[start:]):
            yield VariantDescription(properties)

    # Finish by the null variant
    yield VariantDescription()
