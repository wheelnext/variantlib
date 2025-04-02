from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from typing import Any

import pytest

from variantlib.base import KeyConfigType
from variantlib.base import PluginType
from variantlib.loader import PluginLoader
from variantlib.models.provider import KeyConfig
from variantlib.models.provider import ProviderConfig


class MockedPluginA(PluginType):
    namespace = "test_plugin"

    def get_all_configs(self) -> list[KeyConfigType]:
        return [
            KeyConfig("key1", ["val1a", "val1b", "val1c", "val1d"]),
            KeyConfig("key2", ["val2a", "val2b", "val2c"]),
        ]

    def get_supported_configs(self) -> list[KeyConfigType]:
        return [
            KeyConfig("key1", ["val1a", "val1b"]),
            KeyConfig("key2", ["val2a", "val2b", "val2c"]),
        ]


MyKeyConfig = namedtuple("MyKeyConfig", ("key", "values"))


# NB: this plugin deliberately does not inherit from PluginType
# to test that we don't rely on that inheritance
class MockedPluginB:
    namespace = "second_plugin"

    def get_all_configs(self) -> list[MyKeyConfig]:
        return [
            MyKeyConfig("key3", ["val3a", "val3b", "val3c"]),
        ]

    def get_supported_configs(self) -> list[MyKeyConfig]:
        return [
            MyKeyConfig("key3", ["val3a"]),
        ]


class MyFlag:
    key: str
    values: list[str]

    def __init__(self, key: str) -> None:
        self.key = key
        self.values = ["on"]


class MockedPluginC(PluginType):
    namespace = "incompatible_plugin"

    def get_all_configs(self) -> list[KeyConfigType]:
        return [
            MyFlag("flag1"),
            MyFlag("flag2"),
            MyFlag("flag3"),
            MyFlag("flag4"),
        ]

    def get_supported_configs(self) -> list[KeyConfigType]:
        return []


class ClashingPlugin(PluginType):
    namespace = "test_plugin"

    def get_all_configs(self) -> list[KeyConfigType]:
        return [
            KeyConfig("key1", ["val1a", "val1b", "val1c", "val1d"]),
        ]

    def get_supported_configs(self) -> list[KeyConfigType]:
        return []


class ExceptionTestingPlugin(PluginType):
    namespace = "exception_test"

    def __init__(self, returned_value: Any) -> None:
        self.returned_value = returned_value

    def get_all_configs(self) -> list[KeyConfigType]:
        return self.returned_value

    def get_supported_configs(self) -> list[KeyConfigType]:
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


@pytest.fixture(scope="session")
def mocked_plugin_loader(session_mocker):
    session_mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="test_plugin",
            value="tests.test_plugins:MockedPluginA",
            dist=MockedDistribution(name="test-plugin", version="1.2.3"),
            plugin=MockedPluginA,
        ),
        MockedEntryPoint(
            name="second_plugin",
            value="tests.test_plugins:MockedPluginB",
            dist=MockedDistribution(name="second-plugin", version="4.5.6"),
            plugin=MockedPluginB,
        ),
        MockedEntryPoint(
            name="incompatible_plugin",
            value="tests.test_plugins:MockedPluginC",
            plugin=MockedPluginC,
        ),
    ]
    PluginLoader.flush_cache()
    PluginLoader.load_plugins()
    yield PluginLoader
    PluginLoader.flush_cache()


def test_get_all_configs(mocked_plugin_loader: type[PluginLoader]):
    assert mocked_plugin_loader.get_all_configs() == {
        "incompatible_plugin": ProviderConfig(
            namespace="incompatible_plugin",
            configs=[
                KeyConfig("flag1", ["on"]),
                KeyConfig("flag2", ["on"]),
                KeyConfig("flag3", ["on"]),
                KeyConfig("flag4", ["on"]),
            ],
        ),
        "second_plugin": ProviderConfig(
            namespace="second_plugin",
            configs=[
                KeyConfig("key3", ["val3a", "val3b", "val3c"]),
            ],
        ),
        "test_plugin": ProviderConfig(
            namespace="test_plugin",
            configs=[
                KeyConfig("key1", ["val1a", "val1b", "val1c", "val1d"]),
                KeyConfig("key2", ["val2a", "val2b", "val2c"]),
            ],
        ),
    }


def test_get_supported_configs(mocked_plugin_loader: type[PluginLoader]):
    assert mocked_plugin_loader.get_supported_configs() == {
        "second_plugin": ProviderConfig(
            namespace="second_plugin",
            configs=[
                KeyConfig("key3", ["val3a"]),
            ],
        ),
        "test_plugin": ProviderConfig(
            namespace="test_plugin",
            configs=[
                KeyConfig("key1", ["val1a", "val1b"]),
                KeyConfig("key2", ["val2a", "val2b", "val2c"]),
            ],
        ),
    }


def test_get_dist_name_mapping(mocked_plugin_loader: type[PluginLoader]):
    assert mocked_plugin_loader.distribution_names == {
        "second_plugin": "second-plugin",
        "test_plugin": "test-plugin",
    }


def test_namespace_clash(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="test_plugin",
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
        match="Two plugins found using the same namespace test_plugin. Refusing to "
        "proceed. Please uninstall one of them: test-plugin or test-plugin",
    ):
        PluginLoader.load_plugins()


def test_get_all_configs_incorrect_list_type(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:ExceptionTestingPlugin",
            plugin=ExceptionTestingPlugin(
                (KeyConfig("k1", ["v1"]), KeyConfig("k2", ["v2"]))
            ),
        ),
    ]
    PluginLoader.flush_cache()
    PluginLoader.load_plugins()
    with pytest.raises(
        TypeError,
        match=r"Provider exception_test, get_all_configs\(\) method returned incorrect "
        r"type <class 'tuple'>, excepted: list\[KeyConfig\]",
    ):
        PluginLoader.get_all_configs()


def test_get_all_configs_incorrect_list_length(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:ExceptionTestingPlugin",
            plugin=ExceptionTestingPlugin([]),
        ),
    ]
    PluginLoader.flush_cache()
    PluginLoader.load_plugins()
    with pytest.raises(
        ValueError,
        match=r"Provider exception_test, get_all_configs\(\) method returned no valid "
        r"configs",
    ):
        PluginLoader.get_all_configs()


def test_get_all_configs_incorrect_list_member_type(mocker):
    mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="exception_test",
            value="tests.test_plugins:ExceptionTestingPlugin",
            plugin=ExceptionTestingPlugin([{"k1": ["v1"], "k2": ["v2"]}]),
        ),
    ]
    PluginLoader.flush_cache()
    PluginLoader.load_plugins()
    with pytest.raises(
        TypeError,
        match=r"Provider exception_test, get_all_configs\(\) method returned incorrect "
        r"list member type <class 'dict'>, excepted: KeyConfig",
    ):
        PluginLoader.get_all_configs()
