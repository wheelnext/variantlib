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

    @staticmethod
    def get_all_configs() -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig(
                "name1", ["val1a", "val1b", "val1c", "val1d"], multi_value=False
            ),
            VariantFeatureConfig(
                "name2", ["val2a", "val2b", "val2c"], multi_value=True
            ),
        ]

    @staticmethod
    def get_supported_configs() -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b"], multi_value=False),
            VariantFeatureConfig(
                "name2", ["val2a", "val2b", "val2c"], multi_value=True
            ),
        ]


MyVariantFeatureConfig = namedtuple(
    "MyVariantFeatureConfig", ("name", "values", "multi_value")
)


# NB: this plugin deliberately does not inherit from PluginType
# to test that we don't rely on that inheritance
class MockedPluginB:
    namespace = "second_namespace"

    @classmethod
    def get_all_configs(cls) -> list[MyVariantFeatureConfig]:
        return [
            MyVariantFeatureConfig(
                "name3", ["val3a", "val3b", "val3c"], multi_value=False
            ),
        ]

    @classmethod
    def get_supported_configs(cls) -> list[MyVariantFeatureConfig]:
        return [
            MyVariantFeatureConfig("name3", ["val3a"], multi_value=False),
        ]


class MyFlag:
    name: str
    values: list[str]

    def __init__(self, name: str) -> None:
        self.name = name
        self.values = ["on"]


class MockedPluginC(PluginType):
    namespace = "incompatible_namespace"

    @classmethod
    def get_all_configs(cls) -> list[VariantFeatureConfigType]:
        return [
            MyVariantFeatureConfig(x, ["on"], multi_value=False)
            for x in ("flag1", "flag2", "flag3", "flag4")
        ]

    @staticmethod
    def get_supported_configs() -> list[VariantFeatureConfigType]:
        return []


class MockedAoTPlugin(PluginType):
    namespace = "aot_plugin"

    is_aot_plugin = True

    @staticmethod
    def get_all_configs() -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b"], multi_value=False),
            VariantFeatureConfig(
                "name2", ["val2a", "val2b", "val2c"], multi_value=False
            ),
        ]

    @staticmethod
    def get_supported_configs() -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b"], multi_value=False),
            VariantFeatureConfig(
                "name2", ["val2a", "val2b", "val2c"], multi_value=False
            ),
        ]


class MultiValueAoTPlugin(PluginType):
    namespace = "aot_plugin"

    is_aot_plugin = True

    @staticmethod
    def get_all_configs() -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a"], multi_value=True),
        ]

    @staticmethod
    def get_supported_configs() -> list[VariantFeatureConfigType]:
        return [
            VariantFeatureConfig("name1", ["val1a"], multi_value=True),
        ]


class IndirectPath:
    class MoreIndirection:
        object_a = MockedPluginA()


OBJECT_B = MockedPluginB()
