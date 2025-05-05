from __future__ import annotations

import re
from typing import Any

import pytest

from variantlib.errors import PluginError
from variantlib.errors import PluginMissingError
from variantlib.loader import PluginLoader
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.validators import ValidationError

RANDOM_STUFF = 123


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


def test_get_all_configs(mocked_plugin_loader: PluginLoader):
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


def test_get_supported_configs(mocked_plugin_loader: PluginLoader):
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


def test_namespace_clash():
    loader = PluginLoader()
    loader.load_plugin("tests.mocked_plugins:MockedPluginA")
    with pytest.raises(
        RuntimeError,
        match="Two plugins found using the same namespace test_namespace. Refusing to "
        "proceed.",
    ):
        loader.load_plugin("tests.test_plugins:ClashingPlugin")


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_type(method: str, mocker):
    mocker.patch(
        "variantlib.loader.PluginLoader.plugins",
        new={
            "exception_test": ExceptionTestingPlugin(
                (VariantFeatureConfig("k1", ["v1"]), VariantFeatureConfig("k2", ["v2"]))
            ),
        },
    )
    with pytest.raises(
        TypeError,
        match=re.escape(
            f"Provider exception_test, {method}() method returned incorrect type. "
            "Expected list[variantlib.protocols.VariantFeatureConfigType], "
            "got <class 'tuple'>"
        ),
    ):
        getattr(PluginLoader(), method)()


def test_get_all_configs_incorrect_list_length(mocker):
    mocker.patch(
        "variantlib.loader.PluginLoader.plugins",
        new={
            "exception_test": ExceptionTestingPlugin([]),
        },
    )
    with pytest.raises(
        ValueError,
        match=r"Provider exception_test, get_all_configs\(\) method returned no valid "
        r"configs",
    ):
        PluginLoader().get_all_configs()


@pytest.mark.parametrize("method", ["get_all_configs", "get_supported_configs"])
def test_get_configs_incorrect_list_member_type(method: str, mocker):
    mocker.patch(
        "variantlib.loader.PluginLoader.plugins",
        new={
            "exception_test": ExceptionTestingPlugin([{"k1": ["v1"], "k2": ["v2"]}, 1]),
        },
    )
    with pytest.raises(
        TypeError,
        match=re.escape(
            f"Provider exception_test, {method}() method returned incorrect type. "
            "Expected list[variantlib.protocols.VariantFeatureConfigType], "
            "got list[typing.Union[variantlib.protocols.VariantFeatureConfigType, "
        )
        + r"(dict, int|int, dict)",
    ):
        getattr(PluginLoader(), method)()


def test_namespace_missing_module():
    with pytest.raises(
        PluginError,
        match=r"Loading the plugin from entry point 'tests.no_such_module:foo' failed: "
        r"No module named 'tests.no_such_module'",
    ):
        PluginLoader().load_plugin("tests.no_such_module:foo")


def test_namespace_incorrect_name():
    with pytest.raises(
        PluginError,
        match=r"Loading the plugin from entry point 'tests.test_plugins:no_such_name' "
        r"failed: module 'tests.test_plugins' has no attribute 'no_such_name'",
    ):
        PluginLoader().load_plugin("tests.test_plugins:no_such_name")


class IncompletePlugin:
    namespace = "incomplete_plugin"

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


def test_namespace_incorrect_type():
    with pytest.raises(
        PluginError,
        match=r"Entry point 'tests.test_plugins:RANDOM_STUFF' points at a value that "
        r"is not callable: 123",
    ):
        PluginLoader().load_plugin("tests.test_plugins:RANDOM_STUFF")


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
        match=r"Instantiating the plugin from entry point "
        r"'tests.test_plugins:RaisingInstantiationPlugin' failed: "
        r"I failed to initialize",
    ):
        PluginLoader().load_plugin("tests.test_plugins:RaisingInstantiationPlugin")


class CrossTypeInstantiationPlugin:
    namespace = "cross_plugin"

    def __new__(cls) -> IncompletePlugin:  # type: ignore[misc]
        return IncompletePlugin()

    def get_all_configs(self) -> list[VariantFeatureConfigType]:
        return []

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


@pytest.mark.parametrize("cls", ["IncompletePlugin", "CrossTypeInstantiationPlugin"])
def test_namespace_instantiation_returns_incorrect_type(cls: type, mocker):
    with pytest.raises(
        PluginError,
        match=rf"Instantiating the plugin from entry point 'tests.test_plugins:{cls}' "
        r"returned an object that does not meet the PluginType prototype: "
        r"<tests.test_plugins.IncompletePlugin object at .*> "
        r"\(missing attributes: get_all_configs\)",
    ):
        PluginLoader().load_plugin(f"tests.test_plugins:{cls}")


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


def test_namespaces(mocked_plugin_loader: PluginLoader):
    assert mocked_plugin_loader.namespaces == [
        "test_namespace",
        "second_namespace",
        "incompatible_namespace",
    ]


def test_load_plugin():
    loader = PluginLoader()
    loader.load_plugin("tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_a")
    assert "test_namespace" in loader.plugins
    assert "second_namespace" not in loader.plugins

    loader.load_plugin("tests.mocked_plugins:IndirectPath.MoreIndirection.plugin_b")
    assert "test_namespace" in loader.plugins
    assert "second_namespace" in loader.plugins


def test_load_plugin_invalid_arg():
    with pytest.raises(ValidationError):
        PluginLoader().load_plugin("tests.mocked_plugins")
