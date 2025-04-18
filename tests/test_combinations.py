from __future__ import annotations

import itertools
import json
import random
import string
from pathlib import Path
from typing import TYPE_CHECKING

import jsondiff
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
    config_custom_hw = ProviderConfig(
        namespace="custom_hw",
        configs=[
            VariantFeatureConfig(
                name="driver_version", values=["1.3", "1.2", "1.1", "1"]
            ),
            VariantFeatureConfig(name="hw_architecture", values=["3.4", "3"]),
        ],
    )

    config_networking = ProviderConfig(
        namespace="networking",
        configs=[
            VariantFeatureConfig(name="speed", values=["10GBPS", "1GBPS", "100MBPS"]),
        ],
    )

    return [config_custom_hw, config_networking]


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


def test_get_combinations(configs):
    """Test `get_combinations` yields the expected result in the right order."""
    result = [vdesc.serialize() for vdesc in get_combinations(configs)]

    json_file = Path("tests/artifacts/expected.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the JSON file
    with json_file.open() as f:
        expected = json.load(f)

    differences = jsondiff.diff(result, expected)
    assert not differences, f"Serialization altered JSON: {differences}"


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
