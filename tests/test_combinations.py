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

from tests.test_plugins import mocked_plugin_loader  # noqa: F401
from variantlib.combination import filtered_sorted_variants
from variantlib.loader import PluginLoader
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def configs(mocked_plugin_loader: type[PluginLoader]):  # noqa: F811
    return list(PluginLoader.get_supported_configs().values())


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
    val1a = VariantProperty("test_namespace", "name1", "val1a")
    val1b = VariantProperty("test_namespace", "name1", "val1b")
    val2a = VariantProperty("test_namespace", "name2", "val2a")
    val2b = VariantProperty("test_namespace", "name2", "val2b")
    val2c = VariantProperty("test_namespace", "name2", "val2c")
    val3a = VariantProperty("second_namespace", "name3", "val3a")

    assert list(get_combinations(configs)) == [
        VariantDescription([val1a, val2a, val3a]),
        VariantDescription([val1a, val2a]),
        VariantDescription([val1a, val2b, val3a]),
        VariantDescription([val1a, val2b]),
        VariantDescription([val1a, val2c, val3a]),
        VariantDescription([val1a, val2c]),
        VariantDescription([val1a, val3a]),
        VariantDescription([val1a]),
        VariantDescription([val1b, val2a, val3a]),
        VariantDescription([val1b, val2a]),
        VariantDescription([val1b, val2b, val3a]),
        VariantDescription([val1b, val2b]),
        VariantDescription([val1b, val2c, val3a]),
        VariantDescription([val1b, val2c]),
        VariantDescription([val1b, val3a]),
        VariantDescription([val1b]),
        VariantDescription([val2a, val3a]),
        VariantDescription([val2a]),
        VariantDescription([val2b, val3a]),
        VariantDescription([val2b]),
        VariantDescription([val2c, val3a]),
        VariantDescription([val2c]),
        VariantDescription([val3a]),
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
