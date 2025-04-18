from __future__ import annotations

import re
import sys
from collections import namedtuple
from dataclasses import dataclass
from typing import Any

import pytest

from variantlib.base import PluginType
from variantlib.base import VariantFeatureConfigType
from variantlib.base import VariantPropertyType
from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.loader import PluginLoader
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

if sys.version_info >= (3, 10):
    from importlib.metadata import EntryPoint
else:
    from importlib_metadata import EntryPoint


class MockedPluginA(PluginType):
    namespace = "test_namespace"

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b", "val1c", "val1d"]),
            VariantFeatureConfig("name2", ["val2a", "val2b", "val2c"]),
        ]

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b"]),
            VariantFeatureConfig("name2", ["val2a", "val2b", "val2c"]),
        ]

    def get_build_setup(
        self, properties: list[VariantPropertyType]
    ) -> dict[str, list[str]]:
        for prop in properties:
            assert prop.namespace == self.namespace
            if prop.feature == "name1":
                return {
                    "cflags": [f"-march={prop.value}"],
                    "cxxflags": [f"-march={prop.value}"],
                    "ldflags": ["-Wl,--test-flag"],
                }
        return {}


MyVariantFeatureConfig = namedtuple("MyVariantFeatureConfig", ("name", "values"))


# NB: this plugin deliberately does not inherit from PluginType
# to test that we don't rely on that inheritance
class MockedPluginB:
    namespace = "second_namespace"

    def get_all_configs(self) -> list[MyVariantFeatureConfig]:
        return [
            MyVariantFeatureConfig("name3", ["val3a", "val3b", "val3c"]),
        ]

    def get_supported_configs(self) -> list[MyVariantFeatureConfig]:
        return [
            MyVariantFeatureConfig("name3", ["val3a"]),
        ]


class MyFlag:
    name: str
    values: list[str]

    def __init__(self, name: str) -> None:
        self.name = name
        self.values = ["on"]


class MockedPluginC(PluginType):
    namespace = "incompatible_namespace"

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return [
            MyFlag("flag1"),
            MyFlag("flag2"),
            MyFlag("flag3"),
            MyFlag("flag4"),
        ]

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_build_setup(
        self, properties: list[VariantPropertyType]
    ) -> dict[str, list[str]]:
        flag_opts = []

        for prop in properties:
            assert prop.namespace == self.namespace
            assert prop.value == "on"
            flag_opts.append(f"-m{prop.feature}")

        return {
            "cflags": flag_opts,
            "cxxflags": flag_opts,
        }


class ClashingPlugin(PluginType):
    namespace = "test_namespace"

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b", "val1c", "val1d"]),
        ]

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


class ExceptionTestingPlugin(PluginType):
    namespace = "exception_test"

    def __init__(self, returned_value: Any) -> None:
        self.returned_value = returned_value

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return self.returned_value

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return self.returned_value

    def __call__(self) -> ExceptionTestingPlugin:
        """Fake instantiation"""
        return self


@dataclass
class MockedDistribution:
    name: str
    version: str


@dataclass
class MockedEntryPoint:
    name: str | None
    value: str
    plugin: Any
    group: str | None = None
    dist: MockedDistribution | None = None

    def load(self) -> Any:
        return self.plugin


@pytest.fixture
def mocked_plugin_loader(session_mocker):
    session_mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="test_namespace",
            value="tests.test_plugins:MockedPluginA",
            dist=MockedDistribution(name="test-plugin", version="1.2.3"),
            plugin=MockedPluginA,
        ),
        MockedEntryPoint(
            name="second_namespace",
            value="tests.test_plugins:MockedPluginB",
            dist=MockedDistribution(name="second-plugin", version="4.5.6"),
            plugin=MockedPluginB,
        ),
        MockedEntryPoint(
            name="incompatible_namespace",
            value="tests.test_plugins:MockedPluginC",
            plugin=MockedPluginC,
        ),
    ]

    return PluginLoader


def test_get_all_configs(mocked_plugin_loader: type[PluginLoader]):
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


def test_get_supported_configs(mocked_plugin_loader: type[PluginLoader]):
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


def test_get_dist_name_mapping(mocked_plugin_loader: type[PluginLoader]):
    assert mocked_plugin_loader.distribution_names == {
        "second_namespace": "second-plugin",
        "test_namespace": "test-plugin",
    }


def test_namespace_clash(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="test_namespace",
            value="tests.test_plugins:MockedPluginA",
            dist=MockedDistribution(name="test-plugin", version="1.2.3"),
            plugin=MockedPluginA,
        ),
        MockedEntryPoint(
            name="clashing_plugin",
            value="tests.test_plugins:ClashingPlugin",
            dist=MockedDistribution(name="clashing-plugin", version="4.5.6"),
            plugin=ClashingPlugin,
        ),
    ]
    with pytest.raises(
        RuntimeError,
        match="Two plugins found using the same namespace test_namespace. Refusing to "
        "proceed. Please uninstall one of them: test-plugin or clashing-plugin",
    ):
        PluginLoader.load_plugins()


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_type(method: str, mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:ExceptionTestingPlugin",
            plugin=ExceptionTestingPlugin(
                (VariantFeatureConfig("k1", ["v1"]), VariantFeatureConfig("k2", ["v2"]))
            ),
        ),
    ]
    with pytest.raises(
        TypeError,
        match=re.escape(
            f"Provider exception_test, {method}() method returned incorrect type. "
            "Expected list[variantlib.base.VariantFeatureConfigType], "
            "got <class 'tuple'>"
        ),
    ):
        getattr(PluginLoader, method)()


def test_get_all_configs_incorrect_list_length(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:ExceptionTestingPlugin",
            plugin=ExceptionTestingPlugin([]),
        ),
    ]
    with pytest.raises(
        ValueError,
        match=r"Provider exception_test, get_all_configs\(\) method returned no valid "
        r"configs",
    ):
        PluginLoader.get_all_configs()


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_member_type(method: str, mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:ExceptionTestingPlugin",
            plugin=ExceptionTestingPlugin([{"k1": ["v1"], "k2": ["v2"]}, 1]),
        ),
    ]
    with pytest.raises(
        TypeError,
        match=re.escape(
            f"Provider exception_test, {method}() method returned incorrect type. "
            "Expected list[variantlib.base.VariantFeatureConfigType], "
            "got list[typing.Union[variantlib.base.VariantFeatureConfigType, "
        )
        + r"(dict, int|int, dict)",
    ):
        getattr(PluginLoader, method)()


def test_namespace_missing_module(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        EntryPoint(
            name="exception_test",
            value="tests.no_such_module",
            group="variantlib.plugins",
        ),
    ]

    with pytest.raises(
        PluginError,
        match="Loading the plugin from entry point exception_test failed: "
        "No module named 'tests.no_such_module'",
    ):
        PluginLoader.load_plugins()


def test_namespace_incorrect_name(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        EntryPoint(
            name="exception_test",
            value="tests.test_plugins:no_such_name",
            group="variantlib.plugins",
        ),
    ]

    with pytest.raises(
        PluginError,
        match="Loading the plugin from entry point exception_test failed: "
        "module 'tests.test_plugins' has no attribute 'no_such_name'",
    ):
        PluginLoader.load_plugins()


class IncompletePlugin:
    namespace = "incomplete_plugin"

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


@pytest.mark.parametrize("val", [None, 42, "a-string", {}])
def test_namespace_incorrect_type(val: Any, mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:random_stuff",
            plugin=val,
        ),
    ]

    with pytest.raises(
        PluginError,
        match="Entry point exception_test points at a value that is not callable: "
        f"{val!r}",
    ):
        PluginLoader.load_plugins()


class RaisingInstantiationPlugin:
    namespace = "raising_plugin"

    def __init__(self) -> None:
        raise RuntimeError("I failed to initialize")

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


def test_namespace_instantiation_raises(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:random_stuff",
            plugin=RaisingInstantiationPlugin,
        ),
    ]

    with pytest.raises(
        PluginError,
        match="Instantiating the plugin from entry point exception_test failed: "
        "I failed to initialize",
    ):
        PluginLoader.load_plugins()


class CrossTypeInstantiationPlugin:
    namespace = "cross_plugin"

    def __new__(cls) -> IncompletePlugin:  # type: ignore[misc]
        return IncompletePlugin()

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


@pytest.mark.parametrize("cls", [IncompletePlugin, CrossTypeInstantiationPlugin])
def test_namespace_instantiation_returns_incorrect_type(cls: type, mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:random_stuff",
            plugin=cls,
        ),
    ]

    with pytest.raises(
        PluginError,
        match=r"Instantiating the plugin from entry point exception_test returned "
        r"an object that does not meet the PluginType prototype: "
        r"<tests.test_plugins.IncompletePlugin object at .*> "
        r"\(missing attributes: get_all_configs\)",
    ):
        PluginLoader.load_plugins()


def test_get_build_setup(mocked_plugin_loader):
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


def test_get_build_setup_missing_plugin(mocked_plugin_loader):
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
        assert mocked_plugin_loader.get_build_setup(variant_desc) == {}
