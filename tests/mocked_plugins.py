from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from typing import Any

from variantlib.models.provider import VariantFeatureConfig
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.protocols import VariantPropertyType


@dataclass
class MockedEntryPoint:
    name: str | None
    value: str
    plugin: Any
    group: str | None = None

    def load(self) -> Any:
        return self.plugin

    @property
    def dist(self) -> None:
        return None


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


class IndirectPath:
    class MoreIndirection:
        @classmethod
        def plugin_a(cls) -> MockedPluginA:
            return MockedPluginA()

        @staticmethod
        def plugin_b() -> MockedPluginB:
            return MockedPluginB()
