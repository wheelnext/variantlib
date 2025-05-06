from __future__ import annotations

import json
from pathlib import Path

import pytest

from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.pyproject_toml import ProviderInfo
from variantlib.validators import ValidationError
from variantlib.variants_json import VariantsJson


def test_validate_variants_json():
    json_file = Path("tests/artifacts/variants.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the Variants JSON file
    with json_file.open() as f:
        data = json.load(f)

    variants_json = VariantsJson.from_dict(data)
    assert variants_json.variants == {
        "03e04d5e": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="architecture",
                    value="mother",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value="4",
                ),
            ],
        ),
        "36028aca": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="architecture",
                    value="deepthought",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_accuracy",
                    value="10",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value="10",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="humor",
                    value="0",
                ),
                VariantProperty(
                    namespace="fictional_tech",
                    feature="quantum",
                    value="foam",
                ),
            ],
        ),
        "3f7188c1": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="architecture",
                    value="hal9000",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_accuracy",
                    value="0",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value="6",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="humor",
                    value="2",
                ),
            ],
        ),
        "7db6d39f": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_tech",
                    feature="quantum",
                    value="superposition",
                ),
                VariantProperty(
                    namespace="fictional_tech",
                    feature="risk_exposure",
                    value="25",
                ),
                VariantProperty(
                    namespace="fictional_tech",
                    feature="technology",
                    value="auto_chef",
                ),
            ],
        ),
        "808c7f9d": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_tech",
                    feature="quantum",
                    value="foam",
                ),
                VariantProperty(
                    namespace="fictional_tech",
                    feature="risk_exposure",
                    value="1000000000",
                ),
                VariantProperty(
                    namespace="fictional_tech",
                    feature="technology",
                    value="improb_drive",
                ),
            ],
        ),
        "80fa16ff": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="architecture",
                    value="tars",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_accuracy",
                    value="8",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value="8",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="humor",
                    value="10",
                ),
            ],
        ),
    }
    assert variants_json.namespace_priorities == ["fictional_hw", "fictional_tech"]
    assert variants_json.feature_priorities == [
        VariantFeature(namespace="fictional_tech", feature="quantum")
    ]
    assert variants_json.property_priorities == [
        VariantProperty(
            namespace="fictional_tech", feature="technology", value="auto_chef"
        )
    ]
    assert variants_json.providers == {
        "fictional_hw": ProviderInfo(
            requires=["provider-fictional-hw == 1.0.0"],
            plugin_api="provider_fictional_hw.plugin:FictionalHWPlugin",
        ),
        "fictional_tech": ProviderInfo(
            requires=["provider-fictional-tech == 1.0.0"],
            plugin_api="provider_fictional_tech.plugin:FictionalTechPlugin",
        ),
    }


def test_validate_variants_json_empty():
    assert VariantsJson.from_dict({"variants": {}}).variants == {}


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"variants": ["abcd1234"]},
        {"variants": {"abcd12345": {}}},
        {"variants": {"abcd1234": {}}},
        {"variants": {"abcd1234": ["namespace"]}},
        {"variants": {"abcd1234": {"namespace": [{"feature": "value"}]}}},
        {"variants": {"abcd1234": {"namespace": {}}}},
        {"variants": {"abcd1234": {"namespace": {"feature": 1}}}},
        {"variants": {"abcd1234": {"namespace": {"feature": "variant@python"}}}},
        {"variants": {"abcd1234": {"namespace": {"feature@variant": "python"}}}},
        {"variants": {"abcd1234": {"namesp@ce": {"feature": "value"}}}},
    ],
)
def test_validate_variants_json_incorrect_vhash(data: dict):
    with pytest.raises(ValidationError):
        VariantsJson.from_dict(data)
