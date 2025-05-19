from __future__ import annotations

import json
import re
import sys
from abc import ABC
from abc import abstractproperty
from dataclasses import dataclass
from email import message_from_string
from typing import Any

import pytest

from variantlib.dist_metadata import DistMetadata
from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import EntryPointPluginLoader
from variantlib.plugins.loader import ManualPluginLoader
from variantlib.plugins.loader import PluginLoader
from variantlib.plugins.py_envs import ExternalNonIsolatedPythonEnv
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


class ExceptionPluginBase(PluginType, ABC):
    namespace = "exception_test"

    @abstractproperty
    def returned_value(self) -> Any: ...

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return self.returned_value

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return self.returned_value


def test_get_all_configs(
    mocked_plugin_loader: BasePluginLoader,
):
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
):
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


def test_manual_loading(mocked_plugin_apis: list[str]):
    loader = ManualPluginLoader()
    for plugin_api in mocked_plugin_apis:
        loader.load_plugin(plugin_api)

    assert list(loader.get_supported_configs().keys()) == [
        "test_namespace",
        "second_namespace",
    ]


def test_namespace_clash():
    loader = ManualPluginLoader()
    loader.load_plugin("tests.mocked_plugins:MockedPluginA")
    with pytest.raises(
        RuntimeError,
        match="Two plugins found using the same namespace test_namespace. Refusing to "
        "proceed.",
    ):
        loader.load_plugin("tests.test_plugins:ClashingPlugin")


class IncorrectListTypePlugin(ExceptionPluginBase):
    returned_value = (
        VariantFeatureConfig("k1", ["v1"]),
        VariantFeatureConfig("k2", ["v2"]),
    )


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_type(method: str):
    loader = ManualPluginLoader()
    loader.load_plugin("tests.test_plugins:IncorrectListTypePlugin")

    with pytest.raises(
        TypeError,
        match=re.escape(
            f"Provider exception_test, {method}() method returned incorrect type. "
            "Expected list[variantlib.protocols.VariantFeatureConfigType], "
            "got <class 'tuple'>"
        ),
    ):
        getattr(loader, method)()


class IncorrectListLengthPlugin(ExceptionPluginBase):
    returned_value = []


def test_get_all_configs_incorrect_list_length():
    loader = ManualPluginLoader()
    loader.load_plugin("tests.test_plugins:IncorrectListLengthPlugin")

    with pytest.raises(
        ValueError,
        match=r"Provider exception_test, get_all_configs\(\) method returned no valid "
        r"configs",
    ):
        loader.get_all_configs()


class IncorrectListMemberTypePlugin(ExceptionPluginBase):
    returned_value = [{"k1": ["v1"], "k2": ["v2"]}, 1]


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_member_type(method: str):
    loader = ManualPluginLoader()
    loader.load_plugin("tests.test_plugins:IncorrectListMemberTypePlugin")

    with pytest.raises(
        TypeError,
        match=re.escape(
            f"Provider exception_test, {method}() method returned incorrect type. "
            "Expected list[variantlib.protocols.VariantFeatureConfigType], "
            "got list[typing.Union[variantlib.protocols.VariantFeatureConfigType, "
        )
        + r"(dict, int|int, dict)",
    ):
        getattr(loader, method)()


def test_namespace_missing_module():
    with pytest.raises(
        PluginError,
        match=r"Loading the plugin from 'tests.no_such_module:foo' failed: "
        r"No module named 'tests.no_such_module'",
    ):
        ManualPluginLoader().load_plugin("tests.no_such_module:foo")


def test_namespace_incorrect_name():
    with pytest.raises(
        PluginError,
        match=r"Loading the plugin from 'tests.test_plugins:no_such_name' "
        r"failed: module 'tests.test_plugins' has no attribute 'no_such_name'",
    ):
        ManualPluginLoader().load_plugin("tests.test_plugins:no_such_name")


class IncompletePlugin:
    namespace = "incomplete_plugin"

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


def test_namespace_incorrect_type():
    with pytest.raises(
        PluginError,
        match=r"'tests.test_plugins:RANDOM_STUFF' points at a value that "
        r"is not callable: 123",
    ):
        ManualPluginLoader().load_plugin("tests.test_plugins:RANDOM_STUFF")


class RaisingInstantiationPlugin:
    namespace = "raising_plugin"

    def __init__(self) -> None:
        raise RuntimeError("I failed to initialize")

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


def test_namespace_instantiation_raises():
    with pytest.raises(
        PluginError,
        match=r"Instantiating the plugin from "
        r"'tests.test_plugins:RaisingInstantiationPlugin' failed: "
        r"I failed to initialize",
    ):
        ManualPluginLoader().load_plugin(
            "tests.test_plugins:RaisingInstantiationPlugin"
        )


class CrossTypeInstantiationPlugin:
    namespace = "cross_plugin"

    def __new__(cls) -> IncompletePlugin:  # type: ignore[misc]
        return IncompletePlugin()

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


@pytest.mark.parametrize("cls", ["IncompletePlugin", "CrossTypeInstantiationPlugin"])
def test_namespace_instantiation_returns_incorrect_type(cls: type):
    with pytest.raises(
        PluginError,
        match=rf"Instantiating the plugin from 'tests.test_plugins:{cls}' "
        r"returned an object that does not meet the PluginType prototype: "
        r"<tests.test_plugins.IncompletePlugin object at .*> "
        r"\(missing attributes: get_all_configs\)",
    ):
        ManualPluginLoader().load_plugin(f"tests.test_plugins:{cls}")


def test_get_build_setup(
    mocked_plugin_loader: BasePluginLoader,
):
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
):
    variant_desc = VariantDescription(
        [
            VariantProperty("test_namespace", "name1", "val1b"),
            VariantProperty("missing_plugin", "name", "val"),
        ]
    )

    with pytest.raises(
        PluginMissingError,
        match=r"No plugin found for namespace missing_plugin",
    ):
        assert mocked_plugin_loader.get_build_setup(variant_desc)


def test_namespaces(
    mocked_plugin_loader: BasePluginLoader,
):
    assert mocked_plugin_loader.namespaces == [
        "test_namespace",
        "second_namespace",
        "incompatible_namespace",
    ]


def test_load_plugin():
    loader = ManualPluginLoader()
    loader.load_plugin("tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_a")
    assert loader.namespaces == ["test_namespace"]

    loader.load_plugin("tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_b")
    assert loader.namespaces == ["test_namespace", "second_namespace"]


def test_manual_plugin_loader_as_context_manager():
    with ManualPluginLoader() as loader:
        loader.load_plugin("tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_a")
        assert loader.namespaces == ["test_namespace"]

        loader.load_plugin("tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_b")
        assert loader.namespaces == ["test_namespace", "second_namespace"]

    assert not loader.namespaces


def test_load_plugin_invalid_arg():
    with pytest.raises(ValidationError):
        ManualPluginLoader().load_plugin("tests.mocked_plugins")


@pytest.mark.parametrize(
    "metadata",
    [
        VariantMetadata(
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
        DistMetadata(
            message_from_string("""\
Metadata-Version: 2.1
Name: test-package
Version: 1.2.3
Variant-property: test_namespace :: name1 :: val1a
Variant-property: second_namespace :: name3 :: val3c
Variant-hash: faf70e73
Variant-plugin-api: test_namespace: tests.mocked_plugins:MockedPluginA
Variant-plugin-api: second_namespace: tests.mocked_plugins:MockedPluginB
Variant-default-namespace-priorities: test_namespace, second_namespace
""")
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
def test_load_plugins_from_metadata(metadata: VariantMetadata):
    with (
        ExternalNonIsolatedPythonEnv() as py_ctx,
        PluginLoader(metadata, py_ctx) as loader,
    ):
        assert set(loader.namespaces) == {"test_namespace", "second_namespace"}


@dataclass
class MockedEntryPoint:
    name: str | None
    value: str
    dist: None = None


def test_load_plugins_from_entry_points(mocker):
    mocker.patch("variantlib.plugins.loader.entry_points")().select.return_value = [
        MockedEntryPoint("test", "tests.mocked_plugins:MockedPluginA"),
        MockedEntryPoint("second", "tests.mocked_plugins:MockedPluginB"),
    ]
    with (
        ExternalNonIsolatedPythonEnv() as py_ctx,
        EntryPointPluginLoader(py_ctx) as loader,
    ):
        assert set(loader.namespaces) == {"test_namespace", "second_namespace"}
