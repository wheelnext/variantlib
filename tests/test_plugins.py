from dataclasses import dataclass
from typing import Any, Optional

import pytest

from variantlib.base import PluginBase
from variantlib.config import KeyConfig, ProviderConfig
from variantlib.meta import VariantDescription, VariantMeta
from variantlib.plugins import PluginLoader


class MockedPluginA(PluginBase):
    namespace = "test_plugin"

    def get_supported_configs(self) -> Optional[ProviderConfig]:
        return ProviderConfig(
            namespace=self.namespace,
            configs=[
                KeyConfig("key1", ["val1a", "val1b"]),
                KeyConfig("key2", ["val2a", "val2b", "val2c"]),
            ],
        )

    def get_variant_labels(self, variant_desc: VariantDescription) -> list[str]:
        for meta in variant_desc:
            if meta.namespace == self.namespace and meta.key == "key1":
                return [meta.value.removeprefix("val")]
        return []


# NB: this plugin deliberately does not inherit from PluginBase
# to test that we don't rely on that inheritance
class MockedPluginB:
    namespace = "second_plugin"

    def get_supported_configs(self) -> Optional[ProviderConfig]:
        return ProviderConfig(
            namespace=self.namespace,
            configs=[
                KeyConfig("key3", ["val3a"]),
            ],
        )

    def get_variant_labels(self, variant_desc: VariantDescription) -> list[str]:
        if VariantMeta(self.namespace, "key3", "val3a") in variant_desc:
            return ["sec"]
        return []


class MockedPluginC(PluginBase):
    namespace = "other_plugin"

    def get_supported_configs(self) -> Optional[ProviderConfig]:
        return None

    def get_variant_labels(self, variant_desc: VariantDescription) -> list[str]:
        ret = []
        for meta in variant_desc:
            if meta.namespace == self.namespace and meta.value == "on":
                ret.append(meta.key)
        return ret


class ClashingPlugin(PluginBase):
    namespace = "test_plugin"

    def get_supported_configs(self) -> Optional[ProviderConfig]:
        return None

    def get_variant_labels(self, variant_desc: VariantDescription) -> list[str]:
        ret = []
        for meta in variant_desc:
            if meta.namespace == self.namespace and meta.value == "on":
                ret.append(meta.key)
        return ret


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
    yield PluginLoader()


def test_get_supported_configs(mocked_plugin_loader):
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


def test_get_dist_name_mapping(mocked_plugin_loader):
    assert mocked_plugin_loader.get_dist_name_mapping() == {
        "second_plugin": "second-plugin",
        "test_plugin": "test-plugin",
    }


def test_namespace_clash(mocker):
    mocker.patch("variantlib.plugins.entry_points")().select.return_value = [
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
    mocker.patch("variantlib.metaclasses.SingletonMetaClass._instances", [])
    with pytest.raises(RuntimeError) as exc:
        PluginLoader()
    assert "same namespace test_plugin" in str(exc)
    assert "test-plugin" in str(exc)
    assert "clashing-plugin" in str(exc)


@pytest.mark.parametrize("variant_desc,expected",
[
    (VariantDescription([
        VariantMeta("test_plugin", "key1", "val1a"),
        VariantMeta("test_plugin", "key2", "val2b"),
        VariantMeta("second_plugin", "key3", "val3a"),
        VariantMeta("other_plugin", "flag2", "on"),
    ]), ["1a", "sec", "flag2"]),
    (VariantDescription([
        # note that VariantMetas don't actually have to be supported
        # by the system in question -- we could be cross-building
        # for another system
        VariantMeta("test_plugin", "key1", "val1f"),
        VariantMeta("test_plugin", "key2", "val2b"),
        VariantMeta("second_plugin", "key3", "val3a"),
    ]), ["1f", "sec"]),
    (VariantDescription([
        VariantMeta("test_plugin", "key2", "val2b"),
        VariantMeta("second_plugin", "key3", "val3a"),
    ]), ["sec"]),
    (VariantDescription([
        VariantMeta("test_plugin", "key2", "val2b"),
    ]), []),
    (VariantDescription([
        VariantMeta("test_plugin", "key2", "val2b"),
        VariantMeta("other_plugin", "flag1", "on"),
        VariantMeta("other_plugin", "flag2", "on"),
    ]), ["flag1", "flag2"]),
])
def test_get_variant_labels(mocked_plugin_loader, variant_desc, expected):
    assert mocked_plugin_loader.get_variant_labels(variant_desc) == expected
