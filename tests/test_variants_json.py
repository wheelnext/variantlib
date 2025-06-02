from __future__ import annotations

import json
from pathlib import Path

import pytest

from variantlib.dist_metadata import DistMetadata
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.variants_json import VariantsJson


def test_validate_variants_json():
    json_file = Path("tests/artifacts/variants.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the Variants JSON file
    with json_file.open() as f:
        data = json.load(f)

    variants_json = VariantsJson(data)
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
            enable_if="python_version >= '3.12'",
            plugin_api="provider_fictional_hw.plugin:FictionalHWPlugin",
        ),
        "fictional_tech": ProviderInfo(
            requires=["provider-fictional-tech == 1.0.0"],
            plugin_api="provider_fictional_tech.plugin:FictionalTechPlugin",
        ),
    }


def test_validate_variants_json_empty():
    assert VariantsJson({"variants": {}}).variants == {}


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
        VariantsJson(data)


@pytest.mark.parametrize("cls", [DistMetadata, VariantPyProjectToml, VariantsJson])
def test_conversion(cls: type[DistMetadata | VariantPyProjectToml | VariantsJson]):
    json_file = Path("tests/artifacts/variants.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the Variants JSON file
    with json_file.open() as f:
        data = json.load(f)

    # Convert
    variants_json = VariantsJson(data)
    converted = cls(variants_json)

    # Mangle variants_json to ensure everything was copied
    variants_json.namespace_priorities.append("ns")
    variants_json.feature_priorities.append(VariantFeature("ns", "foo"))
    variants_json.property_priorities.append(VariantProperty("ns", "foo", "bar"))
    variants_json.providers["ns"] = ProviderInfo(plugin_api="foo:bar")
    variants_json.providers["fictional_hw"].enable_if = None
    variants_json.providers["fictional_tech"].requires.append("frobnicate")

    assert converted.namespace_priorities == ["fictional_hw", "fictional_tech"]
    assert converted.feature_priorities == [
        VariantFeature(namespace="fictional_tech", feature="quantum")
    ]
    assert converted.property_priorities == [
        VariantProperty(
            namespace="fictional_tech", feature="technology", value="auto_chef"
        )
    ]
    assert converted.providers == {
        "fictional_hw": ProviderInfo(
            requires=["provider-fictional-hw == 1.0.0"],
            enable_if="python_version >= '3.12'",
            plugin_api="provider_fictional_hw.plugin:FictionalHWPlugin",
        ),
        "fictional_tech": ProviderInfo(
            requires=["provider-fictional-tech == 1.0.0"],
            plugin_api="provider_fictional_tech.plugin:FictionalTechPlugin",
        ),
    }

    # Non-common fields should be reset to defaults
    if isinstance(converted, DistMetadata):
        assert converted.variant_hash == "00000000"
        assert converted.variant_desc == VariantDescription()
    if isinstance(converted, VariantsJson):
        assert converted.variants == {}


def test_to_str() -> None:
    variants_json = VariantsJson(
        VariantMetadata(
            namespace_priorities=["ns2", "ns1"],
            feature_priorities=[
                VariantFeature("ns2", "f2"),
                VariantFeature("ns1", "f1"),
            ],
            property_priorities=[
                VariantProperty("ns2", "f2", "v2"),
                VariantProperty("ns1", "f1", "v1"),
            ],
            providers={
                "ns1": ProviderInfo(
                    requires=["ns1-pkg >= 1.0.0", "ns1-dep"],
                    enable_if="python_version >= '3.12'",
                    plugin_api="ns1_pkg:Plugin",
                ),
                "ns2": ProviderInfo(requires=["ns2_pkg"], plugin_api="ns2_pkg:Plugin"),
            },
        )
    )
    vdesc1 = VariantDescription(
        [
            VariantProperty("ns1", "f1", "v1"),
            VariantProperty("ns2", "f2", "v1"),
        ]
    )
    vdesc2 = VariantDescription(
        [
            VariantProperty("ns2", "f2", "v2"),
        ]
    )
    variants_json.variants = {
        vdesc1.hexdigest: vdesc1,
        vdesc2.hexdigest: vdesc2,
    }
    assert (
        variants_json.to_str()
        == """\
{
    "$schema": "https://variants-schema.wheelnext.dev/",
    "default-priorities": {
        "namespace": [
            "ns2",
            "ns1"
        ],
        "feature": [
            "ns2 :: f2",
            "ns1 :: f1"
        ],
        "property": [
            "ns2 :: f2 :: v2",
            "ns1 :: f1 :: v1"
        ]
    },
    "providers": {
        "ns1": {
            "requires": [
                "ns1-pkg >= 1.0.0",
                "ns1-dep"
            ],
            "enable-if": "python_version >= '3.12'",
            "plugin-api": "ns1_pkg:Plugin"
        },
        "ns2": {
            "requires": [
                "ns2_pkg"
            ],
            "plugin-api": "ns2_pkg:Plugin"
        }
    },
    "variants": {
        "b3b0305c": {
            "ns1": {
                "f1": "v1"
            },
            "ns2": {
                "f2": "v1"
            }
        },
        "9177ff3f": {
            "ns2": {
                "f2": "v2"
            }
        }
    }
}\
"""
    )


def test_roundtrip() -> None:
    json_file = Path("tests/artifacts/variants.json")
    data = json_file.read_text()
    variants_json = VariantsJson(json.loads(data))
    assert variants_json.to_str() == data.rstrip()
