import json
from pathlib import Path
import random
import string

from hypothesis import assume
from hypothesis import example
from hypothesis import given
from hypothesis import strategies as st
import jsondiff
import pytest
from variantlib.combination import filtered_sorted_variants
from variantlib.combination import get_combinations
from variantlib.config import KeyConfig
from variantlib.config import ProviderConfig
from variantlib.meta import VariantDescription


@pytest.fixture(scope="session")
def configs():
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


def desc_to_json(desc_list: list[VariantDescription]) -> dict:
    shuffled_desc_list = list(desc_list)
    random.shuffle(shuffled_desc_list)
    for desc in shuffled_desc_list:
        variant_dict = {}
        for variant_meta in desc:
            provider_dict = variant_dict.setdefault(variant_meta.provider, {})
            provider_dict[variant_meta.key] = variant_meta.value
        yield (desc.hexdigest, variant_dict)


def test_filtered_sorted_variants_roundtrip(configs):
    """Test that we can round-trip all combinations via variants.json and get the same result."""
    combinations = list(get_combinations(configs))
    variants_from_json = {k: v for k, v in desc_to_json(combinations)}
    assert filtered_sorted_variants(variants_from_json, configs) == combinations


@example(
    [
        ProviderConfig(
            provider="A",
            configs=[
                KeyConfig(key="A1", values=["x"]),
                KeyConfig(key="A2", values=["x"]),
            ],
        ),
        ProviderConfig(provider="B", configs=[KeyConfig(key="B1", values=["x"])]),
        ProviderConfig(provider="C", configs=[KeyConfig(key="C1", values=["x"])]),
    ]
)
@given(
    st.lists(
        min_size=1,
        max_size=3,
        unique_by=lambda provider_cfg: provider_cfg.provider,
        elements=st.builds(
            ProviderConfig,
            provider=st.text(
                string.ascii_letters + string.digits + "_", min_size=1, max_size=64
            ),
            configs=st.lists(
                min_size=1,
                max_size=2,
                unique_by=lambda key_cfg: key_cfg.key,
                elements=st.builds(
                    KeyConfig,
                    key=st.text(
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
    variants_from_json = {k: v for k, v in desc_to_json(combinations)}
    assert filtered_sorted_variants(variants_from_json, configs) == combinations
