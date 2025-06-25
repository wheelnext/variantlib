from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_FEATURE_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROPERTY_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
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
        "3351fc6a": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value=str(value),
                )
                for value in range(4, 6)
            ]
        ),
        "181830db": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value=str(value),
                )
                for value in range(4, 8)
            ]
        ),
        "72c47fce": VariantDescription(
            properties=[
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value="7",
                ),
                VariantProperty(
                    namespace="fictional_hw",
                    feature="compute_capability",
                    value="8",
                ),
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
    assert VariantsJson({VARIANTS_JSON_VARIANT_DATA_KEY: {}}).variants == {}


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
        VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
        VARIANT_INFO_DEFAULT_PRIO_KEY: {
            VARIANT_INFO_NAMESPACE_KEY: ["ns2", "ns1"],
            VARIANT_INFO_FEATURE_KEY: {"ns1": ["f1"], "ns2": ["f2"]},
            VARIANT_INFO_PROPERTY_KEY: {"ns2": {"f2": ["v2"]}, "ns1": {"f1": ["v1"]}},
        },
        VARIANT_INFO_PROVIDER_DATA_KEY: {
            "ns1": {
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["ns1-pkg >= 1.0.0", "ns1-dep"],
                VARIANT_INFO_PROVIDER_ENABLE_IF_KEY: "python_version >= '3.12'",
                VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "ns1_pkg:Plugin",
            },
            "ns2": {
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["ns2_pkg"],
                VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "ns2_pkg:Plugin",
            },
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
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
        VARIANT_INFO_NAMESPACE_KEY: ["a", "b"],
        VARIANT_INFO_FEATURE_KEY: {"a": ["a"], "b": ["b"]},
        VARIANT_INFO_PROPERTY_KEY: {"a": {"a": ["a"]}, "b": {"b": ["b"]}},
    }

    provider_b: ProviderPluginJsonDict = {
        VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["b"],
        VARIANT_INFO_PROVIDER_ENABLE_IF_KEY: "python_version > '3.12'",
        VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "b:B",
    }

    json_a: VariantsJsonDict = {
        VARIANT_INFO_DEFAULT_PRIO_KEY: default_prios,
        VARIANT_INFO_PROVIDER_DATA_KEY: {
            "a": {
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["a"],
                VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "a:A",
            },
            "b": provider_b,
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
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
        VARIANT_INFO_DEFAULT_PRIO_KEY: default_prios,
        VARIANT_INFO_PROVIDER_DATA_KEY: {
            "a": {
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["a2"],
                VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "a:A",
            },
            "b": provider_b,
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
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
            VARIANT_INFO_DEFAULT_PRIO_KEY: default_prios,
            VARIANT_INFO_PROVIDER_DATA_KEY: {
                "a": {
                    VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["a", "a2"],
                    VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "a:A",
                },
                "b": provider_b,
            },
            VARIANTS_JSON_VARIANT_DATA_KEY: {
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
        VARIANT_INFO_NAMESPACE_KEY: ["b", "a"],
        VARIANT_INFO_FEATURE_KEY: {"b": ["b"]},
        VARIANT_INFO_PROPERTY_KEY: {"b": {"b": ["b"]}},
    }

    for key in json_a[VARIANT_INFO_DEFAULT_PRIO_KEY]:
        _json_data = copy.deepcopy(json_b)
        _json_data[VARIANT_INFO_DEFAULT_PRIO_KEY][key] = overrides[key]  # type: ignore[literal-required]
        with pytest.raises(ValidationError, match=rf"Inconsistency in '{key}"):
            v1.merge(VariantsJson(_json_data))

    # Test for mismatches in provider information.
    _json_data = copy.deepcopy(json_b)
    del _json_data[VARIANT_INFO_PROVIDER_DATA_KEY]["b"][
        VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
    ]
    with pytest.raises(
        ValidationError, match=r"Inconsistency in providers\['b'\].enable_if"
    ):
        v1.merge(VariantsJson(_json_data))

    _json_data = copy.deepcopy(json_b)
    _json_data[VARIANT_INFO_PROVIDER_DATA_KEY]["a"][
        VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
    ] = "test:Test"
    with pytest.raises(
        ValidationError, match=r"Inconsistency in providers\['a'\].plugin_api"
    ):
        v1.merge(VariantsJson(_json_data))
