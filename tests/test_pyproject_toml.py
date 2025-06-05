from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.constants import VARIANT_METADATA_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_METADATA_FEATURE_KEY
from variantlib.constants import VARIANT_METADATA_NAMESPACE_KEY
from variantlib.constants import VARIANT_METADATA_PROPERTY_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_REQUIRES_KEY
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.variant import VariantProperty
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.variants_json import VariantsJson

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from typing import Any


TOML_DATA = """
[project]
name = "frobnicate"
version = "1.2.3"

[variant.default-priorities]
namespace = ["ns1", "ns2"]
feature.ns1 = ["f2"]
feature.ns2 = ["f1", "f2"]
property = ["ns1 :: f2 :: p1", "ns2 :: f1 :: p2"]

[variant.providers.ns1]
requires = ["ns1-provider >= 1.2.3"]
enable-if = "python_version >= '3.12'"
plugin-api = "ns1_provider.plugin:NS1Plugin"

[variant.providers.ns2]
requires = [
    "ns2_provider; python_version >= '3.11'",
    "old_ns2_provider; python_version < '3.11'",
]
plugin-api = "ns2_provider:Plugin"
"""

PYPROJECT_TOML = tomllib.loads(TOML_DATA)

PYPROJECT_TOML_MINIMAL = tomllib.loads(
    # remove truly optional keys
    "\n".join(
        x for x in TOML_DATA.splitlines() if not x.startswith(("feature", "property"))
    )
)


def test_pyproject_toml() -> None:
    pyproj = VariantPyProjectToml(PYPROJECT_TOML)
    assert pyproj.namespace_priorities == ["ns1", "ns2"]
    assert pyproj.feature_priorities == {
        "ns1": ["f2"],
        "ns2": ["f1", "f2"],
    }
    assert pyproj.property_priorities == [
        VariantProperty("ns1", "f2", "p1"),
        VariantProperty("ns2", "f1", "p2"),
    ]
    assert pyproj.providers == {
        "ns1": ProviderInfo(
            requires=["ns1-provider >= 1.2.3"],
            enable_if="python_version >= '3.12'",
            plugin_api="ns1_provider.plugin:NS1Plugin",
        ),
        "ns2": ProviderInfo(
            requires=[
                "ns2_provider; python_version >= '3.11'",
                "old_ns2_provider; python_version < '3.11'",
            ],
            plugin_api="ns2_provider:Plugin",
        ),
    }


def test_pyproject_toml_minimal() -> None:
    pyproj = VariantPyProjectToml(PYPROJECT_TOML_MINIMAL)
    assert pyproj.namespace_priorities == ["ns1", "ns2"]
    assert pyproj.feature_priorities == {}
    assert pyproj.property_priorities == []
    assert pyproj.providers == {
        "ns1": ProviderInfo(
            requires=["ns1-provider >= 1.2.3"],
            enable_if="python_version >= '3.12'",
            plugin_api="ns1_provider.plugin:NS1Plugin",
        ),
        "ns2": ProviderInfo(
            requires=[
                "ns2_provider; python_version >= '3.11'",
                "old_ns2_provider; python_version < '3.11'",
            ],
            plugin_api="ns2_provider:Plugin",
        ),
    }


def test_invalid_top_type() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\: expected dict\[str, typing\.Any\], "
        r"got <class 'list'>",
    ):
        VariantPyProjectToml({PYPROJECT_TOML_TOP_KEY: [123]})


@pytest.mark.parametrize(
    "table", [VARIANT_METADATA_DEFAULT_PRIO_KEY, VARIANT_METADATA_PROVIDER_DATA_KEY]
)
def test_invalid_table_type(table: str) -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{table}: expected dict\[str, "
        r"typing\.Any\], got <class 'list'>",
    ):
        VariantPyProjectToml({PYPROJECT_TOML_TOP_KEY: {table: [123]}})


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (VARIANT_METADATA_NAMESPACE_KEY, r"list\[str\]"),
        (VARIANT_METADATA_FEATURE_KEY, r"dict\[str, list\[str\]\]"),
        (VARIANT_METADATA_PROPERTY_KEY, r"list\[str\]"),
    ],
)
def test_invalid_priority_type(key: str, expected: str) -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_DEFAULT_PRIO_KEY}\."
        rf"{key}: expected {expected}, got <class 'str'>",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_DEFAULT_PRIO_KEY: {key: "frobnicate"}
                }
            }
        )


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        (
            VARIANT_METADATA_NAMESPACE_KEY,
            ["ns", "ns :: feature"],
            r"\[1\]: Value `ns :: feature`",
        ),
        (
            VARIANT_METADATA_FEATURE_KEY,
            {"ns": ["feature", "feature :: property"]},
            r"\.ns\[1\]: Value `feature :: property`",
        ),
        (
            VARIANT_METADATA_PROPERTY_KEY,
            ["ns :: feature :: property", "ns :: feature"],
            r"\[1\]: Value `ns :: feature`",
        ),
    ],
)
def test_invalid_priority_value(key: str, value: Any, expected: str) -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_DEFAULT_PRIO_KEY}\."
        rf"{key}{expected} must match regex",
    ):
        VariantPyProjectToml(
            {PYPROJECT_TOML_TOP_KEY: {VARIANT_METADATA_DEFAULT_PRIO_KEY: {key: value}}}
        )


def test_invalid_provider_namespace() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY}"
        r"\[0\]: Value `invalid namespace` must match regex",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {"invalid namespace": {}}
                }
            }
        )


def test_invalid_provider_table_type() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY}\."
        r"ns: expected dict\[str, typing.Any\], got <class 'list'>",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {"ns": [123]}
                }
            }
        )


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (VARIANT_METADATA_PROVIDER_REQUIRES_KEY, r"list\[str\]"),
        (VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY, r"<class 'str'>"),
    ],
)
def test_invalid_provider_data_type(key: str, expected: str) -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY}\.ns\."
        rf"{key}: expected {expected}, got <class 'int'>",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {"ns": {key: 123}}
                }
            }
        )


def test_invalid_provider_requires() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY}\.ns\."
        rf"{VARIANT_METADATA_PROVIDER_REQUIRES_KEY}\[1\]: Value `` must match regex",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {
                        "ns": {
                            VARIANT_METADATA_PROVIDER_REQUIRES_KEY: [
                                "frobnicator >= 123",
                                "",
                            ]
                        }
                    }
                }
            }
        )


def test_invalid_provider_plugin_api() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY}\.ns\."
        rf"{VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY}: Value `frobnicate` must match "
        r"regex",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {
                        "ns": {VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY: "frobnicate"}
                    }
                }
            }
        )


def test_missing_provider_plugin_api() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY}\.ns\."
        rf"{VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY}: required key not found",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {
                        "ns": {VARIANT_METADATA_PROVIDER_REQUIRES_KEY: ["frobnicate"]}
                    }
                }
            }
        )


def test_missing_namespace_priority() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_DEFAULT_PRIO_KEY}\."
        rf"{VARIANT_METADATA_NAMESPACE_KEY} must specify the same namespaces as "
        rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY} "
        r"keys; currently: set\(\) vs\. \{'ns'\}",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {
                        "ns": {
                            VARIANT_METADATA_PROVIDER_REQUIRES_KEY: ["frobnicate"],
                            VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY: "foo:Plugin",
                        }
                    }
                }
            }
        )


def test_missing_namespace_provider() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_DEFAULT_PRIO_KEY}\."
        rf"{VARIANT_METADATA_NAMESPACE_KEY} must specify the same namespaces as "
        rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY} "
        r"keys; currently: \{'ns'\} vs\. set\(\)",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_DEFAULT_PRIO_KEY: {
                        VARIANT_METADATA_NAMESPACE_KEY: ["ns"]
                    }
                }
            }
        )


def test_extra_default_priority_key() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_DEFAULT_PRIO_KEY}: "
        r"unexpected subkeys: \{'foo'\}",
    ):
        VariantPyProjectToml(
            {PYPROJECT_TOML_TOP_KEY: {VARIANT_METADATA_DEFAULT_PRIO_KEY: {"foo": {}}}}
        )


def test_extra_provider_data_key() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_METADATA_PROVIDER_DATA_KEY}\."
        r"ns: unexpected subkeys: \{'foo'\}",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_METADATA_PROVIDER_DATA_KEY: {
                        "ns": {
                            "plugin-api": "frobnicate:Plugin",
                            "foo": {},
                        }
                    }
                }
            }
        )


@pytest.mark.parametrize("cls", [VariantPyProjectToml, VariantsJson])
def test_conversion(cls: type[VariantPyProjectToml | VariantsJson]) -> None:
    pyproj = VariantPyProjectToml(PYPROJECT_TOML)
    converted = cls(pyproj)

    # Mangle the original to ensure everything was copied
    pyproj.namespace_priorities.append("ns4")
    pyproj.feature_priorities["ns4"] = ["foo"]
    pyproj.property_priorities.append(VariantProperty("ns4", "foo", "bar"))
    pyproj.providers["ns4"] = ProviderInfo(plugin_api="foo:bar")
    pyproj.providers["ns1"].enable_if = None
    pyproj.providers["ns2"].requires.append("frobnicate")

    assert converted.namespace_priorities == ["ns1", "ns2"]
    assert converted.feature_priorities == {
        "ns1": ["f2"],
        "ns2": ["f1", "f2"],
    }
    assert converted.property_priorities == [
        VariantProperty("ns1", "f2", "p1"),
        VariantProperty("ns2", "f1", "p2"),
    ]
    assert converted.providers == {
        "ns1": ProviderInfo(
            requires=["ns1-provider >= 1.2.3"],
            enable_if="python_version >= '3.12'",
            plugin_api="ns1_provider.plugin:NS1Plugin",
        ),
        "ns2": ProviderInfo(
            requires=[
                "ns2_provider; python_version >= '3.11'",
                "old_ns2_provider; python_version < '3.11'",
            ],
            plugin_api="ns2_provider:Plugin",
        ),
    }

    # Non-common fields should be reset to defaults
    if isinstance(converted, VariantsJson):
        assert converted.variants == {}


def test_get_provider_requires() -> None:
    pyproj = VariantPyProjectToml(PYPROJECT_TOML)
    assert pyproj.get_provider_requires() == {
        "ns1-provider >= 1.2.3",
        "ns2_provider; python_version >= '3.11'",
        "old_ns2_provider; python_version < '3.11'",
    }
    assert pyproj.get_provider_requires({"ns1"}) == {
        "ns1-provider >= 1.2.3",
    }
    assert pyproj.get_provider_requires({"ns2"}) == {
        "ns2_provider; python_version >= '3.11'",
        "old_ns2_provider; python_version < '3.11'",
    }
    with pytest.raises(KeyError):
        pyproj.get_provider_requires({"no_ns"})
