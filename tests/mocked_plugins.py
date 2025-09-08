from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass

from variantlib.models.provider import VariantFeatureConfig
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType


@dataclass
class MockedEntryPoint:
    name: str | None
    value: str
    dist: None = None


class MockedPluginA(PluginType):
    namespace = "test_namespace"  # pyright: ignore[reportAssignmentType,reportIncompatibleMethodOverride]

    has_fixed_supported_configs = True

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
            MyVariantFeatureConfig(x, ["on"])
            for x in ("flag1", "flag2", "flag3", "flag4")
        ]

    def get_supported_configs(self) -> list[VariantFeatureConfigType]:
        return []


class IndirectPath:
    class MoreIndirection:
        @classmethod
        def plugin_a(cls) -> MockedPluginA:
            return MockedPluginA()

        @staticmethod
        def plugin_b() -> MockedPluginB:
            return MockedPluginB()

        object_a = MockedPluginA()


OBJECT_B = MockedPluginB()
