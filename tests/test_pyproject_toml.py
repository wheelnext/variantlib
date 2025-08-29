from __future__ import annotations

import sys
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_FEATURE_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROPERTY_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_OPTIONAL_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.errors import ValidationError
from variantlib.models.variant_info import PluginUse
from variantlib.models.variant_info import ProviderInfo
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.variants_json import VariantsJson

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from typing import Any


TOML_DATA = f"""
[project]
name = "frobnicate"
version = "1.2.3"

[{PYPROJECT_TOML_TOP_KEY}.{VARIANT_INFO_DEFAULT_PRIO_KEY}]
{VARIANT_INFO_NAMESPACE_KEY} = ["ns1", "ns2"]
{VARIANT_INFO_FEATURE_KEY}.ns1 = ["f2"]
{VARIANT_INFO_FEATURE_KEY}.ns2 = ["f1", "f2"]
{VARIANT_INFO_PROPERTY_KEY}.ns1.f2 = ["p1"]
{VARIANT_INFO_PROPERTY_KEY}.ns2.f1 = ["p2"]

[{PYPROJECT_TOML_TOP_KEY}.{VARIANT_INFO_PROVIDER_DATA_KEY}.ns1]
{VARIANT_INFO_PROVIDER_REQUIRES_KEY} = ["ns1-provider >= 1.2.3"]
{VARIANT_INFO_PROVIDER_ENABLE_IF_KEY} = "python_version >= '3.12'"
{VARIANT_INFO_PROVIDER_PLUGIN_API_KEY} = "ns1_provider.plugin:NS1Plugin"

[{PYPROJECT_TOML_TOP_KEY}.{VARIANT_INFO_PROVIDER_DATA_KEY}.ns2]
{VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY} = "build"
{VARIANT_INFO_PROVIDER_REQUIRES_KEY} = [
    "ns2_provider; python_version >= '3.11'",
    "old_ns2_provider; python_version < '3.11'",
]
{VARIANT_INFO_PROVIDER_PLUGIN_API_KEY} = "ns2_provider:Plugin"
{VARIANT_INFO_PROVIDER_OPTIONAL_KEY} = true
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
    assert pyproj.property_priorities == {
        "ns1": {"f2": ["p1"]},
        "ns2": {"f1": ["p2"]},
    }
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
            optional=True,
            plugin_api="ns2_provider:Plugin",
            plugin_use=PluginUse.BUILD,
        ),
    }


def test_pyproject_toml_minimal() -> None:
    pyproj = VariantPyProjectToml(PYPROJECT_TOML_MINIMAL)
    assert pyproj.namespace_priorities == ["ns1", "ns2"]
    assert pyproj.feature_priorities == {}
    assert pyproj.property_priorities == {}
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
            optional=True,
            plugin_api="ns2_provider:Plugin",
            plugin_use=PluginUse.BUILD,
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
    "table", [VARIANT_INFO_DEFAULT_PRIO_KEY, VARIANT_INFO_PROVIDER_DATA_KEY]
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
        (VARIANT_INFO_NAMESPACE_KEY, r"list\[str\]"),
        (VARIANT_INFO_FEATURE_KEY, r"dict\[str, list\[str\]\]"),
        (VARIANT_INFO_PROPERTY_KEY, r"dict\[str\, dict\[str, list\[str\]\]\]"),
    ],
)
def test_invalid_priority_type(key: str, expected: str) -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_DEFAULT_PRIO_KEY}\."
        rf"{key}: expected {expected}, got <class 'str'>",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_DEFAULT_PRIO_KEY: {key: "frobnicate"}
                }
            }
        )


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        (
            VARIANT_INFO_NAMESPACE_KEY,
            ["ns", "ns :: feature"],
            r"\[1\]: Value `ns :: feature`",
        ),
        (
            VARIANT_INFO_FEATURE_KEY,
            {"ns": ["feature", "feature :: property"]},
            r"\.ns\[1\]: Value `feature :: property`",
        ),
        (
            VARIANT_INFO_PROPERTY_KEY,
            {"ns": {"feature": ["property", "not valid"]}},
            r".ns.feature\[1\]: Value `not valid`",
        ),
    ],
)
def test_invalid_priority_value(key: str, value: Any, expected: str) -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_DEFAULT_PRIO_KEY}\."
        rf"{key}{expected} must match regex",
    ):
        VariantPyProjectToml(
            {PYPROJECT_TOML_TOP_KEY: {VARIANT_INFO_DEFAULT_PRIO_KEY: {key: value}}}
        )


def test_invalid_provider_namespace() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}"
        r"\[0\]: Value `invalid namespace` must match regex",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_PROVIDER_DATA_KEY: {"invalid namespace": {}}
                }
            }
        )


def test_invalid_provider_table_type() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}\."
        r"ns: expected dict\[str, typing.Any\], got <class 'list'>",
    ):
        VariantPyProjectToml(
            {PYPROJECT_TOML_TOP_KEY: {VARIANT_INFO_PROVIDER_DATA_KEY: {"ns": [123]}}}
        )


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (VARIANT_INFO_PROVIDER_REQUIRES_KEY, r"list\[str\]"),
        (VARIANT_INFO_PROVIDER_PLUGIN_API_KEY, r"<class 'str'>"),
    ],
)
def test_invalid_provider_data_type(key: str, expected: str) -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}\.ns\."
        rf"{key}: expected {expected}, got <class 'int'>",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_PROVIDER_DATA_KEY: {"ns": {key: 123}}
                }
            }
        )


def test_invalid_provider_requires() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}\.ns\."
        rf"{VARIANT_INFO_PROVIDER_REQUIRES_KEY}\[1\]: Value `` must match regex",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_PROVIDER_DATA_KEY: {
                        "ns": {
                            VARIANT_INFO_PROVIDER_REQUIRES_KEY: [
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
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}\.ns\."
        rf"{VARIANT_INFO_PROVIDER_PLUGIN_API_KEY}: Value `foo:bar:baz` must match "
        r"regex",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_PROVIDER_DATA_KEY: {
                        "ns": {VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "foo:bar:baz"}
                    }
                }
            }
        )


def test_invalid_provider_plugin_use() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}\.ns\."
        rf"{VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY}: Expected one of ",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_PROVIDER_DATA_KEY: {
                        "ns": {VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY: "foo"}
                    }
                }
            }
        )


@pytest.mark.parametrize("plugin_use", PluginUse.__members__.values())
def test_missing_provider_plugin_api(plugin_use: PluginUse) -> None:
    expected = (
        pytest.raises(
            ValidationError,
            match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}\.ns: "
            rf"either {VARIANT_INFO_PROVIDER_PLUGIN_API_KEY} or "
            rf"{VARIANT_INFO_PROVIDER_REQUIRES_KEY} must be specified",
        )
        if plugin_use != PluginUse.NONE
        else nullcontext()
    )

    with expected:
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_DEFAULT_PRIO_KEY: {
                        VARIANT_INFO_NAMESPACE_KEY: ["ns"],
                    },
                    VARIANT_INFO_PROVIDER_DATA_KEY: {
                        "ns": {
                            VARIANT_INFO_PROVIDER_REQUIRES_KEY: [],
                            VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY: str(plugin_use),
                        }
                    },
                }
            }
        )


def test_missing_namespace_priority() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_DEFAULT_PRIO_KEY}\."
        rf"{VARIANT_INFO_NAMESPACE_KEY} must specify the same namespaces as "
        rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY} "
        r"keys; currently: set\(\) vs\. \{'ns'\}",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_PROVIDER_DATA_KEY: {
                        "ns": {
                            VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["frobnicate"],
                            VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "foo:Plugin",
                        }
                    }
                }
            }
        )


def test_missing_namespace_provider() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_DEFAULT_PRIO_KEY}\."
        rf"{VARIANT_INFO_NAMESPACE_KEY} must specify the same namespaces as "
        rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY} "
        r"keys; currently: \{'ns'\} vs\. set\(\)",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_DEFAULT_PRIO_KEY: {VARIANT_INFO_NAMESPACE_KEY: ["ns"]}
                }
            }
        )


def test_extra_default_priority_key() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_DEFAULT_PRIO_KEY}: "
        r"unexpected subkeys: \{'foo'\}",
    ):
        VariantPyProjectToml(
            {PYPROJECT_TOML_TOP_KEY: {VARIANT_INFO_DEFAULT_PRIO_KEY: {"foo": {}}}}
        )


def test_extra_provider_data_key() -> None:
    with pytest.raises(
        ValidationError,
        match=rf"{PYPROJECT_TOML_TOP_KEY}\.{VARIANT_INFO_PROVIDER_DATA_KEY}\."
        r"ns: unexpected subkeys: \{'foo'\}",
    ):
        VariantPyProjectToml(
            {
                PYPROJECT_TOML_TOP_KEY: {
                    VARIANT_INFO_PROVIDER_DATA_KEY: {
                        "ns": {
                            VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "frobnicate:Plugin",
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
    pyproj.property_priorities["ns2"]["foo"] = ["bar"]
    pyproj.providers["ns4"] = ProviderInfo(plugin_api="foo:bar")
    pyproj.providers["ns1"].enable_if = None
    pyproj.providers["ns2"].requires.append("frobnicate")

    assert converted.namespace_priorities == ["ns1", "ns2"]
    assert converted.feature_priorities == {
        "ns1": ["f2"],
        "ns2": ["f1", "f2"],
    }
    assert converted.property_priorities == {
        "ns1": {"f2": ["p1"]},
        "ns2": {"f1": ["p2"]},
    }
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
            optional=True,
            plugin_api="ns2_provider:Plugin",
            plugin_use=PluginUse.BUILD,
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


def test_no_plugin_api() -> None:
    pyproject_toml = VariantPyProjectToml(
        {
            PYPROJECT_TOML_TOP_KEY: {
                VARIANT_INFO_DEFAULT_PRIO_KEY: {VARIANT_INFO_NAMESPACE_KEY: ["ns"]},
                VARIANT_INFO_PROVIDER_DATA_KEY: {
                    "ns": {
                        "requires": [
                            "my-plugin[foo] >= 1.2.3; python_version >= '3.10'"
                        ],
                    }
                },
            }
        }
    )
    assert pyproject_toml.providers["ns"].plugin_api is None
    assert pyproject_toml.providers["ns"].object_reference == "my_plugin"


def test_get_package_defined_properties() -> None:
    pyproj = VariantPyProjectToml(PYPROJECT_TOML)
    assert pyproj.get_package_defined_properties() == {
        "ns1": {
            "f2": ["p1"],
        },
        "ns2": {
            "f1": ["p2"],
            "f2": [],
        },
    }
    assert pyproj.get_package_defined_properties({"ns1", "ns2", "ns3"}) == {
        "ns1": {
            "f2": ["p1"],
        },
        "ns2": {
            "f1": ["p2"],
            "f2": [],
        },
    }
    assert pyproj.get_package_defined_properties({"ns1"}) == {
        "ns1": {
            "f2": ["p1"],
        },
    }
    assert pyproj.get_package_defined_properties({"ns3"}) == {}
