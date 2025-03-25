from dataclasses import dataclass
from typing import Any, Optional

import pytest

from variantlib.base import PluginBase
from variantlib.config import KeyConfig, ProviderConfig
from variantlib.plugins import PluginLoader


class MockedPluginA(PluginBase):
    def get_supported_configs(self) -> Optional[ProviderConfig]:
        return ProviderConfig(
            provider="test_plugin",
            configs=[
                KeyConfig("key1", ["val1a", "val1b"]),
                KeyConfig("key2", ["val2a", "val2b", "val2c"]),
            ],
        )


# NB: this plugin deliberately does not inherit from PluginBase
# to test that we don't rely on that inheritance
class MockedPluginB:
    def get_supported_configs(self) -> Optional[ProviderConfig]:
        return ProviderConfig(
            provider="second_plugin",
            configs=[
                KeyConfig("key3", ["val3a"]),
            ],
        )


class MockedPluginC(PluginBase):
    def get_supported_configs(self) -> Optional[ProviderConfig]:
        return None


@dataclass
class MockedDistribution:
    name: str
    version: str


@dataclass
class MockedEntryPoint:
    name: Optional[str]
    value: str
    plugin: Any
    group: Optional[str] = None
    dist: Optional[MockedDistribution] = None

    def load(self) -> Any:
        return self.plugin


@pytest.fixture(scope="session")
def mocked_plugin_loader(session_mocker):
    session_mocker.patch("variantlib.plugins.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="test_plugin",
            value="tests.test_plugins:MockedPluginA",
            dist=MockedDistribution(name="test-plugin", version="1.2.3"),
            plugin=MockedPluginA,
        ),
        MockedEntryPoint(
            name="other_plugin",
            value="tests.test_plugins:MockedPluginB",
            dist=MockedDistribution(name="other-plugin", version="4.5.6"),
            plugin=MockedPluginB,
        ),
        MockedEntryPoint(
            name="incompatible_plugin",
            value="tests.test_plugins:MockedPluginC",
            dist=MockedDistribution(name="incompatible-plugin", version="0.0.0"),
            plugin=MockedPluginC,
        ),
    ]
    yield PluginLoader()


def test_get_supported_configs(mocked_plugin_loader):
    assert mocked_plugin_loader.get_supported_configs() == {
        "other_plugin": ProviderConfig(
            provider="second_plugin",
            configs=[
                KeyConfig("key3", ["val3a"]),
            ],
        ),
        "test_plugin": ProviderConfig(
            provider="test_plugin",
            configs=[
                KeyConfig("key1", ["val1a", "val1b"]),
                KeyConfig("key2", ["val2a", "val2b", "val2c"]),
            ],
        ),
    }


def test_get_dist_name_mapping(mocked_plugin_loader):
    assert mocked_plugin_loader.get_dist_name_mapping() == {
        "incompatible_plugin": "incompatible-plugin",
        "other_plugin": "other-plugin",
        "test_plugin": "test-plugin",
    }
