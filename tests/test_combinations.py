from __future__ import annotations

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
from variantlib.combination import get_combinations
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.models.variant import VariantDescription


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


def desc_to_json(desc_list: list[VariantDescription]) -> Generator:
    shuffled_desc_list = list(desc_list)
    random.shuffle(shuffled_desc_list)
    for desc in shuffled_desc_list:
        variant_dict: dict[str, dict[str, str]] = {}
        for variant_meta in desc:
            provider_dict = variant_dict.setdefault(variant_meta.namespace, {})
            provider_dict[variant_meta.feature] = variant_meta.value
        yield (desc.hexdigest, variant_dict)


def test_filtered_sorted_variants_roundtrip(configs):
    """Test that we can round-trip all combinations via variants.json and get the same
    result."""
    combinations = list(get_combinations(configs))
    variants_from_json = dict(desc_to_json(combinations))
    assert filtered_sorted_variants(variants_from_json, configs) == combinations


@settings(deadline=500)
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
    variants_from_json = dict(desc_to_json(combinations))
    assert filtered_sorted_variants(variants_from_json, configs) == combinations
