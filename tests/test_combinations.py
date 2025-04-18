from __future__ import annotations

import random
import string
from typing import TYPE_CHECKING

import pytest
from hypothesis import assume
from hypothesis import example
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from variantlib.combination import filtered_sorted_variants
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(scope="session")
def configs():
    return [
        ProviderConfig(
            namespace="cuda",
            configs=[
                VariantFeatureConfig(name="driver", values=["12.2", "12.1", "12.0"]),
            ],
        ),
        ProviderConfig(
            namespace="x86_64",
            configs=[
                VariantFeatureConfig(name="aes_ni", values=["on"]),
                VariantFeatureConfig(name="level", values=["v3", "v2", "v1"]),
            ],
        ),
    ]


def get_combinations(
    provider_cfgs: list[ProviderConfig],
) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantProperty` given a list of
    `ProviderConfig`. This function respects ordering and priority provided."""

    assert isinstance(provider_cfgs, (list, tuple))
    assert len(provider_cfgs) > 0
    assert all(isinstance(config, ProviderConfig) for config in provider_cfgs)

    all_properties = [
        (provider_cfg.namespace, feature_cfg.name, feature_cfg.values)
        for provider_cfg in provider_cfgs
        for feature_cfg in provider_cfg.configs
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


def test_get_combinations(configs):
    """Test `get_combinations` yields the expected result in the right order."""
    cuda122 = VariantProperty("cuda", "driver", "12.2")
    cuda121 = VariantProperty("cuda", "driver", "12.1")
    cuda120 = VariantProperty("cuda", "driver", "12.0")
    aesni = VariantProperty("x86_64", "aes_ni", "on")
    x8664v3 = VariantProperty("x86_64", "level", "v3")
    x8664v2 = VariantProperty("x86_64", "level", "v2")
    x8664v1 = VariantProperty("x86_64", "level", "v1")

    assert list(get_combinations(configs)) == [
        VariantDescription([cuda122, aesni, x8664v3]),
        VariantDescription([cuda122, aesni, x8664v2]),
        VariantDescription([cuda122, aesni, x8664v1]),
        VariantDescription([cuda122, aesni]),
        VariantDescription([cuda122, x8664v3]),
        VariantDescription([cuda122, x8664v2]),
        VariantDescription([cuda122, x8664v1]),
        VariantDescription([cuda122]),
        VariantDescription([cuda121, aesni, x8664v3]),
        VariantDescription([cuda121, aesni, x8664v2]),
        VariantDescription([cuda121, aesni, x8664v1]),
        VariantDescription([cuda121, aesni]),
        VariantDescription([cuda121, x8664v3]),
        VariantDescription([cuda121, x8664v2]),
        VariantDescription([cuda121, x8664v1]),
        VariantDescription([cuda121]),
        VariantDescription([cuda120, aesni, x8664v3]),
        VariantDescription([cuda120, aesni, x8664v2]),
        VariantDescription([cuda120, aesni, x8664v1]),
        VariantDescription([cuda120, aesni]),
        VariantDescription([cuda120, x8664v3]),
        VariantDescription([cuda120, x8664v2]),
        VariantDescription([cuda120, x8664v1]),
        VariantDescription([cuda120]),
        VariantDescription([aesni, x8664v3]),
        VariantDescription([aesni, x8664v2]),
        VariantDescription([aesni, x8664v1]),
        VariantDescription([aesni]),
        VariantDescription([x8664v3]),
        VariantDescription([x8664v2]),
        VariantDescription([x8664v1]),
    ]


def vdescs_to_json(vdescs: list[VariantDescription]) -> Generator:
    shuffled_vdescs = list(vdescs)
    random.shuffle(shuffled_vdescs)
    for vdesc in shuffled_vdescs:
        variant_dict: dict[str, dict[str, str]] = {}
        for vprop in vdesc.properties:
            provider_dict = variant_dict.setdefault(vprop.namespace, {})
            provider_dict[vprop.feature] = vprop.value
        yield (vdesc.hexdigest, variant_dict)


def test_filtered_sorted_variants_roundtrip(configs):
    """Test that we can round-trip all combinations via variants.json and get the same
    result."""
    combinations = list(get_combinations(configs))
    variants_from_json = dict(vdescs_to_json(combinations))
    assert filtered_sorted_variants(variants_from_json, configs) == combinations


@settings(deadline=1000)
@example(
    [
        ProviderConfig(
            namespace="A",
            configs=[
                VariantFeatureConfig(name="A1", values=["x"]),
                VariantFeatureConfig(name="A2", values=["x"]),
            ],
        ),
        ProviderConfig(
            namespace="B", configs=[VariantFeatureConfig(name="B1", values=["x"])]
        ),
        ProviderConfig(
            namespace="C", configs=[VariantFeatureConfig(name="C1", values=["x"])]
        ),
    ]
)
@given(
    st.lists(
        min_size=1,
        max_size=3,
        unique_by=lambda provider_cfg: provider_cfg.namespace,
        elements=st.builds(
            ProviderConfig,
            namespace=st.text(
                string.ascii_letters + string.digits + "_", min_size=1, max_size=64
            ),
            configs=st.lists(
                min_size=1,
                max_size=2,
                unique_by=lambda vfeat_cfg: vfeat_cfg.name,
                elements=st.builds(
                    VariantFeatureConfig,
                    name=st.text(
                        alphabet=string.ascii_letters + string.digits + "_",
                        min_size=1,
                        max_size=64,
                    ),
                    values=st.lists(
                        min_size=1,
                        max_size=3,
                        unique=True,
                        elements=st.text(
                            alphabet=string.ascii_letters + string.digits + "_.",
                            min_size=1,
                            max_size=64,
                        ),
                    ),
                ),
            ),
        ),
    )
)
def test_filtered_sorted_variants_roundtrip_fuzz(configs):
    def filter_long_combinations():
        for i, x in enumerate(get_combinations(configs)):
            assume(i < 65536)
            yield x

    combinations = list(filter_long_combinations())
    variants_from_json = dict(vdescs_to_json(combinations))
    assert filtered_sorted_variants(variants_from_json, configs) == combinations
