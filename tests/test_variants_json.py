from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.models.variant_info import ProviderInfo
from variantlib.models.variant_info import VariantInfo
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from variantlib.constants import PriorityJsonDict
    from variantlib.constants import ProviderPluginJsonDict
    from variantlib.constants import VariantsJsonDict


def test_validate_variants_json() -> None:
    json_file = Path(
        "tests/artifacts/variant_json_files/dummy_project-1.0.0-variants.json"
    )
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the Variants JSON file
    with json_file.open() as f:
        data = json.load(f)

    variants_json = VariantsJson(data)
    assert variants_json.variants == {
        "00000000": VariantDescription(),
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
        "1d836653": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value=">=4,<6",
                )
            ]
        ),
        "a0d8855a": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value=">=4,<8",
                )
            ]
        ),
        "092f6ea8": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value=">=7",
                )
            ]
        ),
    }
    assert variants_json.namespace_priorities == ["fictional_hw", "fictional_tech"]
    assert variants_json.feature_priorities == {
        "fictional_hw": ["humor", "compute_accuracy"],
        "fictional_tech": ["quantum"],
    }
    assert variants_json.property_priorities == {
        "fictional_tech": {"technology": ["auto_chef"]}
    }
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


def test_validate_variants_json_empty() -> None:
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
def test_validate_variants_json_incorrect_vhash(data: VariantsJsonDict) -> None:
    with pytest.raises(ValidationError):
        VariantsJson(data)


@pytest.mark.parametrize("cls", [VariantPyProjectToml, VariantsJson])
def test_conversion(cls: type[VariantPyProjectToml | VariantsJson]) -> None:
    json_file = Path(
        "tests/artifacts/variant_json_files/dummy_project-1.0.0-variants.json"
    )
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the Variants JSON file
    with json_file.open() as f:
        data = json.load(f)

    # Convert
    variants_json = VariantsJson(data)
    converted = cls(variants_json)

    # Mangle variants_json to ensure everything was copied
    variants_json.namespace_priorities.append("ns")
    variants_json.feature_priorities["ns"] = ["foo"]
    variants_json.property_priorities["fictional_tech"]["foo"] = ["bar"]
    variants_json.providers["ns"] = ProviderInfo(plugin_api="foo:bar")
    variants_json.providers["fictional_hw"].enable_if = None
    variants_json.providers["fictional_tech"].requires.append("frobnicate")

    assert converted.namespace_priorities == ["fictional_hw", "fictional_tech"]
    assert converted.feature_priorities == {
        "fictional_hw": ["humor", "compute_accuracy"],
        "fictional_tech": ["quantum"],
    }
    assert converted.property_priorities == {
        "fictional_tech": {"technology": ["auto_chef"]}
    }
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
    if isinstance(converted, VariantsJson):
        assert converted.variants == {}


def test_to_str() -> None:
    variants_json = VariantsJson(
        VariantInfo(
            namespace_priorities=["ns2", "ns1"],
            feature_priorities={
                "ns1": ["f1"],
                "ns2": ["f2"],
            },
            property_priorities={
                "ns2": {"f2": ["v2"]},
                "ns1": {"f1": ["v1"]},
            },
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
    assert json.loads(variants_json.to_str()) == {
        "$schema": VARIANTS_JSON_SCHEMA_URL,
        "default-priorities": {
            "namespace": ["ns2", "ns1"],
            "feature": {"ns1": ["f1"], "ns2": ["f2"]},
            "property": {"ns2": {"f2": ["v2"]}, "ns1": {"f1": ["v1"]}},
        },
        "providers": {
            "ns1": {
                "requires": ["ns1-pkg >= 1.0.0", "ns1-dep"],
                "enable-if": "python_version >= '3.12'",
                "plugin-api": "ns1_pkg:Plugin",
            },
            "ns2": {"requires": ["ns2_pkg"], "plugin-api": "ns2_pkg:Plugin"},
        },
        "variants": {
            "b3b0305c": {"ns1": {"f1": ["v1"]}, "ns2": {"f2": ["v1"]}},
            "9177ff3f": {"ns2": {"f2": ["v2"]}},
        },
    }


def test_roundtrip() -> None:
    json_file = Path(
        "tests/artifacts/variant_json_files/dummy_project-1.0.0-variants.json"
    )
    data = json_file.read_text()
    variants_json = VariantsJson(json.loads(data))
    assert json.loads(variants_json.to_str()) == json.loads(data)


def test_merge_variants() -> None:
    default_prios: PriorityJsonDict = {
        "namespace": ["a", "b"],
        "feature": {"a": ["a"], "b": ["b"]},
        "property": {"a": {"a": ["a"]}, "b": {"b": ["b"]}},
    }

    provider_b: ProviderPluginJsonDict = {
        "requires": ["b"],
        "enable-if": "python_version > '3.12'",
        "plugin-api": "b:B",
    }

    json_a: VariantsJsonDict = {
        "default-priorities": default_prios,
        "providers": {
            "a": {
                "requires": ["a"],
                "plugin-api": "a:A",
            },
            "b": provider_b,
        },
        "variants": {
            "54357fe4": {
                "a": {
                    "a": ["a"],
                },
                "b": {
                    "b": ["c"],
                },
            }
        },
    }
    json_b: VariantsJsonDict = {
        "default-priorities": default_prios,
        "providers": {
            "a": {
                "requires": ["a2"],
                "plugin-api": "a:A",
            },
            "b": provider_b,
        },
        "variants": {
            "48b561bc": {
                "a": {
                    "a": ["c"],
                },
                "b": {
                    "b": ["b"],
                },
            }
        },
    }
    merged = VariantsJson(
        {
            "default-priorities": default_prios,
            "providers": {
                "a": {
                    "requires": ["a", "a2"],
                    "plugin-api": "a:A",
                },
                "b": provider_b,
            },
            "variants": {
                "48b561bc": {
                    "a": {
                        "a": ["c"],
                    },
                    "b": {
                        "b": ["b"],
                    },
                },
                "54357fe4": {
                    "a": {
                        "a": ["a"],
                    },
                    "b": {
                        "b": ["c"],
                    },
                },
            },
        }
    )

    # Test that merging itself does not change anything.
    v1 = VariantsJson(json_a)
    v2 = VariantsJson(json_a)
    v1.merge(v2)
    assert v1 == v2

    # Test merging json_b.
    v2 = VariantsJson(json_b)
    v1.merge(v2)
    assert v1 == merged

    # Merging stuff again should not change anything.
    v1.merge(v2)
    assert v1 == merged
    v1.merge(v1)
    assert v1 == merged

    # If we merge the other way around, we should get requires reversed.
    merged.providers["a"].requires.reverse()
    v2.merge(v1)
    assert v2 == merged
    v2.merge(v2)
    assert v2 == merged

    # Merging it back to v1 should not affect order.
    merged.providers["a"].requires.reverse()
    v1.merge(v2)
    assert v1 == merged

    # Test for mismatches in default priorities.
    overrides = {
        "namespace": ["b", "a"],
        "feature": {"b": ["b"]},
        "property": {"b": {"b": ["b"]}},
    }

    for key in json_a["default-priorities"]:
        _json_data = copy.deepcopy(json_b)
        _json_data["default-priorities"][key] = overrides[key]  # type: ignore[literal-required]
        with pytest.raises(ValidationError, match=rf"Inconsistency in '{key}"):
            v1.merge(VariantsJson(_json_data))

    # Test for mismatches in provider information.
    _json_data = copy.deepcopy(json_b)
    del _json_data["providers"]["b"]["enable-if"]
    with pytest.raises(
        ValidationError, match=r"Inconsistency in providers\['b'\].enable_if"
    ):
        v1.merge(VariantsJson(_json_data))

    _json_data = copy.deepcopy(json_b)
    _json_data["providers"]["a"]["plugin-api"] = "test:Test"
    with pytest.raises(
        ValidationError, match=r"Inconsistency in providers\['a'\].plugin_api"
    ):
        v1.merge(VariantsJson(_json_data))
