import json
from pathlib import Path

import jsondiff
from variantlib.combination import get_combinations
from variantlib.config import KeyConfig
from variantlib.config import ProviderConfig


def test_get_combinations():
    """Test `get_combinations` yields the expected result in the right order."""
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

    result = [vdesc.serialize() for vdesc in get_combinations(configs)]

    json_file = Path("tests/artifacts/expected.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the JSON file
    with json_file.open() as f:
        expected = json.load(f)

    differences = jsondiff.diff(result, expected)
    assert not differences, f"Serialization altered JSON: {differences}"
