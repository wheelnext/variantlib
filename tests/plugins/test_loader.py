from __future__ import annotations

import json
import re
import sys

import pytest

from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantInfo
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import EntryPointPluginLoader
from variantlib.plugins.loader import ListPluginLoader
from variantlib.plugins.loader import PluginLoader
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.variants_json import VariantsJson

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


RANDOM_STUFF = 123


class ClashingPlugin(PluginType):
    namespace = "test_namespace"

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b", "val1c", "val1d"]),
        ]

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


class ExceptionPluginBase(PluginType):
    namespace = "exception_test"

    returned_value: list[VariantFeatureConfigType]

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return self.returned_value

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return self.returned_value


def test_get_all_configs(
    mocked_plugin_loader: BasePluginLoader,
) -> None:
    assert mocked_plugin_loader.get_all_configs() == {
        "incompatible_namespace": ProviderConfig(
            namespace="incompatible_namespace",
            configs=[
                VariantFeatureConfig("flag1", ["on"]),
                VariantFeatureConfig("flag2", ["on"]),
                VariantFeatureConfig("flag3", ["on"]),
                VariantFeatureConfig("flag4", ["on"]),
            ],
        ),
        "second_namespace": ProviderConfig(
            namespace="second_namespace",
            configs=[
                VariantFeatureConfig("name3", ["val3a", "val3b", "val3c"]),
            ],
        ),
        "test_namespace": ProviderConfig(
            namespace="test_namespace",
            configs=[
                VariantFeatureConfig("name1", ["val1a", "val1b", "val1c", "val1d"]),
                VariantFeatureConfig("name2", ["val2a", "val2b", "val2c"]),
            ],
        ),
    }


def test_get_supported_configs(
    mocked_plugin_loader: BasePluginLoader,
) -> None:
    assert mocked_plugin_loader.get_supported_configs() == {
        "second_namespace": ProviderConfig(
            namespace="second_namespace",
            configs=[
                VariantFeatureConfig("name3", ["val3a"]),
            ],
        ),
        "test_namespace": ProviderConfig(
            namespace="test_namespace",
            configs=[
                VariantFeatureConfig("name1", ["val1a", "val1b"]),
                VariantFeatureConfig("name2", ["val2a", "val2b", "val2c"]),
            ],
        ),
    }


def test_namespace_clash() -> None:
    with (
        pytest.raises(
            RuntimeError,
            match="Two plugins found using the same namespace test_namespace. Refusing "
            "to proceed.",
        ),
        ListPluginLoader(
            [
                "tests.mocked_plugins:MockedPluginA",
                "tests.plugins.test_loader:ClashingPlugin",
            ]
        ),
    ):
        pass


class IncorrectListTypePlugin(ExceptionPluginBase):
    returned_value = (
        VariantFeatureConfig("k1", ["v1"]),
        VariantFeatureConfig("k2", ["v2"]),
    )  # type: ignore[assignment]


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_type(method: str) -> None:
    with (
        ListPluginLoader(
            ["tests.plugins.test_loader:IncorrectListTypePlugin"]
        ) as loader,
        pytest.raises(
            PluginError,
            match=r".*"
            + re.escape(
                f"Provider exception_test, {method}() method returned incorrect type. "
                "Expected list[_variantlib_protocols.VariantFeatureConfigType], "
                "got <class 'tuple'>"
            ),
        ),
    ):
        getattr(loader, method)()


class IncorrectListLengthPlugin(ExceptionPluginBase):
    returned_value = []


def test_get_all_configs_incorrect_list_length() -> None:
    with (
        ListPluginLoader(
            ["tests.plugins.test_loader:IncorrectListLengthPlugin"]
        ) as loader,
        pytest.raises(
            ValueError,
            match=r"Provider exception_test, get_all_configs\(\) method returned "
            r"no valid configs",
        ),
    ):
        loader.get_all_configs()


class IncorrectListMemberTypePlugin(ExceptionPluginBase):
    returned_value = [{"k1": ["v1"], "k2": ["v2"]}, 1]  # type: ignore[list-item]


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_member_type(method: str) -> None:
    with (
        ListPluginLoader(
            ["tests.plugins.test_loader:IncorrectListMemberTypePlugin"]
        ) as loader,
        pytest.raises(
            PluginError,
            match=r".*"
            + re.escape(
                f"Provider exception_test, {method}() method returned incorrect type. "
                "Expected list[_variantlib_protocols.VariantFeatureConfigType], "
                "got list[typing.Union[_variantlib_protocols.VariantFeatureConfigType, "
            )
            + r"(dict, int|int, dict)",
        ),
    ):
        getattr(loader, method)()


def test_namespace_missing_module() -> None:
    with (
        pytest.raises(
            PluginError,
            match="Loading the plugin from 'tests.no_such_module:foo' failed: "
            "No module named 'tests.no_such_module'",
        ),
        ListPluginLoader(["tests.no_such_module:foo"]),
    ):
        pass


def test_namespace_incorrect_name() -> None:
    with (
        pytest.raises(
            PluginError,
            match="Loading the plugin from 'tests.plugins.test_loader:no_such_name' "
            "failed: module 'tests.plugins.test_loader' has no attribute "
            "'no_such_name'",
        ),
        ListPluginLoader([("tests.plugins.test_loader:no_such_name")]),
    ):
        pass


class IncompletePlugin:
    namespace = "incomplete_plugin"

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


def test_namespace_incorrect_type() -> None:
    with (
        pytest.raises(
            PluginError,
            match=r"'tests.plugins.test_loader:RANDOM_STUFF' does not meet "
            r"the PluginType prototype: 123 \(missing attributes: get_all_configs, "
            r"get_supported_configs, namespace\)",
        ),
        ListPluginLoader(["tests.plugins.test_loader:RANDOM_STUFF"]),
    ):
        pass


class RaisingInstantiationPlugin:
    namespace = "raising_plugin"

    def __init__(self) -> None:
        raise RuntimeError("I failed to initialize")

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


def test_namespace_instantiation_raises() -> None:
    with (
        pytest.raises(
            PluginError,
            match="Instantiating the plugin from "
            "'tests.plugins.test_loader:RaisingInstantiationPlugin' failed: "
            "I failed to initialize",
        ),
        ListPluginLoader(["tests.plugins.test_loader:RaisingInstantiationPlugin"]),
    ):
        pass


class CrossTypeInstantiationPlugin:
    namespace = "cross_plugin"

    def __new__(cls) -> IncompletePlugin:  # type: ignore[misc]
        return IncompletePlugin()

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


@pytest.mark.parametrize("cls", ["IncompletePlugin", "CrossTypeInstantiationPlugin"])
def test_namespace_instantiation_returns_incorrect_type(
    cls: type,
) -> None:
    with (
        pytest.raises(
            PluginError,
            match=re.escape(
                f"'tests.plugins.test_loader:{cls}' does not meet the PluginType "
                "prototype: <tests.plugins.test_loader.IncompletePlugin object at"
            )
            + r".*(missing attributes: get_all_configs)",
        ),
        ListPluginLoader([f"tests.plugins.test_loader:{cls}"]),
    ):
        pass


def test_get_build_setup(
    mocked_plugin_loader: BasePluginLoader,
) -> None:
    variant_desc = VariantDescription(
        [
            VariantProperty("test_namespace", "name1", "val1b"),
            VariantProperty("second_namespace", "name3", "val3c"),
            VariantProperty("incompatible_namespace", "flag1", "on"),
            VariantProperty("incompatible_namespace", "flag4", "on"),
        ]
    )

    assert mocked_plugin_loader.get_build_setup(variant_desc) == {
        "cflags": ["-mflag1", "-mflag4", "-march=val1b"],
        "cxxflags": ["-mflag1", "-mflag4", "-march=val1b"],
        "ldflags": ["-Wl,--test-flag"],
    }


def test_get_build_setup_missing_plugin(
    mocked_plugin_loader: BasePluginLoader,
) -> None:
    variant_desc = VariantDescription(
        [
            VariantProperty("test_namespace", "name1", "val1b"),
            VariantProperty("missing_plugin", "name", "val"),
        ]
    )

    with pytest.raises(
        PluginMissingError,
        match=r"No plugin found for namespace 'missing_plugin'",
    ):
        assert mocked_plugin_loader.get_build_setup(variant_desc)


def test_namespaces(
    mocked_plugin_loader: BasePluginLoader,
) -> None:
    assert mocked_plugin_loader.namespaces == [
        "test_namespace",
        "second_namespace",
        "incompatible_namespace",
    ]


def test_non_class_attrs() -> None:
    with ListPluginLoader(
        [
            "tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_a",
            "tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_b",
        ]
    ) as loader:
        assert loader.namespaces == ["test_namespace", "second_namespace"]


def test_non_callable_plugin() -> None:
    with ListPluginLoader(
        [
            "tests.mocked_plugins:IndirectPath.MoreIndirection.object_a",
            "tests.mocked_plugins:OBJECT_B",
        ]
    ) as loader:
        assert loader.namespaces == ["test_namespace", "second_namespace"]


def test_plugin_module() -> None:
    with ListPluginLoader(
        [
            "tests.mocked_plugin_as_module",
        ]
    ) as loader:
        assert loader.namespaces == ["module_namespace"]


def test_load_plugin_invalid_arg() -> None:
    with (
        pytest.raises(ValidationError),
        ListPluginLoader(["tests.mocked_plugins:foo:bar"]),
    ):
        pass


@pytest.mark.parametrize(
    "metadata",
    [
        VariantInfo(
            namespace_priorities=[
                "test_namespace",
                "second_namespace",
                "incompatible_namespace",
            ],
            providers={
                "test_namespace": ProviderInfo(
                    plugin_api="tests.mocked_plugins:MockedPluginA"
                ),
                "second_namespace": ProviderInfo(
                    # always true
                    enable_if="python_version >= '3.9'",
                    plugin_api="tests.mocked_plugins:MockedPluginB",
                ),
                "incompatible_namespace": ProviderInfo(
                    # always false (hopefully)
                    enable_if='platform_machine == "frobnicator"',
                    plugin_api="tests.mocked_plugins:MockedPluginC",
                ),
            },
        ),
        VariantPyProjectToml(
            tomllib.loads("""
[variant.default-priorities]
namespace = ["test_namespace", "second_namespace"]

[variant.providers.test_namespace]
plugin-api = "tests.mocked_plugins:MockedPluginA"

[variant.providers.second_namespace]
plugin-api = "tests.mocked_plugins:MockedPluginB"
""")
        ),
        VariantsJson(
            json.loads("""
{
    "default-priorities": {
        "namespace": ["test_namespace", "second_namespace"]
    },
    "providers": {
        "test_namespace": {
            "plugin-api": "tests.mocked_plugins:MockedPluginA"
        },
        "second_namespace": {
            "plugin-api": "tests.mocked_plugins:MockedPluginB"
        }
    },
    "variants": {}
}
""")
        ),
    ],
)
def test_load_plugins_from_metadata(metadata: VariantInfo) -> None:
    with PluginLoader(metadata, use_auto_install=False) as loader:
        assert set(loader.namespaces) == {"test_namespace", "second_namespace"}


def test_load_plugins_from_entry_points(mocked_entry_points: None) -> None:
    with EntryPointPluginLoader() as loader:
        assert set(loader.namespaces) == {
            "test_namespace",
            "second_namespace",
            "incompatible_namespace",
        }


def test_install_plugin(test_plugin_package_req: str) -> None:
    metadata = VariantInfo(
        namespace_priorities=["installable_plugin"],
        providers={
            "installable_plugin": ProviderInfo(
                plugin_api="test_plugin_package",
                requires=[test_plugin_package_req],
            ),
        },
    )

    with PluginLoader(metadata, use_auto_install=True, isolated=True) as loader:
        assert set(loader.namespaces) == {"installable_plugin"}


def test_no_plugin_api(test_plugin_package_req: str) -> None:
    metadata = VariantInfo(
        namespace_priorities=["installable_plugin"],
        providers={
            "installable_plugin": ProviderInfo(
                requires=[test_plugin_package_req],
            ),
        },
    )

    with PluginLoader(metadata, use_auto_install=True, isolated=True) as loader:
        assert set(loader.namespaces) == {"installable_plugin"}
