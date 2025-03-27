from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from typing import Any

import pytest
from variantlib.base import PluginBase
from variantlib.config import KeyConfig
from variantlib.config import ProviderConfig
from variantlib.loader import PluginLoader


class MockedPluginA(PluginBase):
    namespace = "test_plugin"

    def get_supported_configs(self) -> list[KeyConfig]:
        return [
            KeyConfig("key1", ["val1a", "val1b"]),
            KeyConfig("key2", ["val2a", "val2b", "val2c"]),
        ]


MyKeyConfig = namedtuple("MyKeyConfig", ("key", "values"))


# NB: this plugin deliberately does not inherit from PluginBase
# to test that we don't rely on that inheritance
class MockedPluginB:
    namespace = "second_plugin"

    def get_supported_configs(self) -> list[MyKeyConfig]:
        return [
            MyKeyConfig("key3", ["val3a"]),
        ]


class MockedPluginC(PluginBase):
    namespace = "incompatible_plugin"

    def get_supported_configs(self) -> list[KeyConfig]:
        return []


class ClashingPlugin(PluginBase):
    namespace = "test_plugin"

    def get_supported_configs(self) -> list[KeyConfig]:
        return []


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
    PluginLoader.load_plugins()
    yield PluginLoader
    PluginLoader.flush_cache()


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
