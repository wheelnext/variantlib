from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass

from variantlib.models.provider import VariantFeatureConfig
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.protocols import VariantPropertyType


@dataclass
class MockedEntryPoint:
    name: str | None
    value: str
    dist: None = None


class MockedPluginA(PluginType):
    namespace = "test_namespace"  # pyright: ignore[reportAssignmentType,reportIncompatibleMethodOverride]

    def validate_property(self, variant_property: VariantPropertyType) -> bool:
        assert variant_property.namespace == self.namespace
        return (
            variant_property.feature == "name1"
            and variant_property.value in ["val1a", "val1b", "val1c", "val1d"]
        ) or (
            variant_property.feature == "name2"
            and variant_property.value in ["val2a", "val2b", "val2c"]
        )

    def get_supported_configs(
        self, known_properties: frozenset[VariantPropertyType] | None
    ) -> list[VariantFeatureConfigType]:
        assert known_properties is None
        return [
            VariantFeatureConfig("name1", ["val1a", "val1b"]),
            VariantFeatureConfig("name2", ["val2a", "val2b", "val2c"]),
        ]


MyVariantFeatureConfig = namedtuple("MyVariantFeatureConfig", ("name", "values"))


# NB: this plugin deliberately does not inherit from PluginType
# to test that we don't rely on that inheritance
class MockedPluginB:
    namespace = "second_namespace"

    def validate_property(self, variant_property: VariantPropertyType) -> bool:
        assert variant_property.namespace == self.namespace
        return variant_property.feature == "name3" and variant_property.value in [
            "val3a",
            "val3b",
            "val3c",
        ]

    def get_supported_configs(
        self, known_properties: frozenset[VariantPropertyType] | None
    ) -> list[MyVariantFeatureConfig]:
        assert known_properties is None
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

    def validate_property(self, variant_property: VariantPropertyType) -> bool:
        assert variant_property.namespace == self.namespace
        return (
            variant_property.feature in ("flag1", "flag2", "flag3", "flag4")
            and variant_property.value == "on"
        )

    def get_supported_configs(
        self, known_properties: frozenset[VariantPropertyType] | None
    ) -> list[VariantFeatureConfigType]:
        assert known_properties is None
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
