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
    dynamic = False  # pyright: ignore[reportAssignmentType,reportIncompatibleMethodOverride]

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

    def get_build_setup(
        self, properties: frozenset[VariantPropertyType]
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
    dynamic = True

    def validate_property(self, variant_property: VariantPropertyType) -> bool:
        assert variant_property.namespace == self.namespace
        return variant_property.feature == "name3"

    def get_supported_configs(
        self, known_properties: frozenset[VariantPropertyType] | None
    ) -> list[MyVariantFeatureConfig]:
        assert known_properties is not None
        assert all(prop.namespace == self.namespace for prop in known_properties)
        vals3 = ["val3a"]
        vals3.extend(
            x.value
            for x in known_properties
            if x.feature == "name3" and x.value not in vals3
        )
        return [
            MyVariantFeatureConfig("name3", vals3),
        ]


class MyFlag:
    name: str
    values: list[str]

    def __init__(self, name: str) -> None:
        self.name = name
        self.values = ["on"]


class MockedPluginC(PluginType):
    namespace = "incompatible_namespace"
    dynamic = False

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

    def get_build_setup(
        self, properties: frozenset[VariantPropertyType]
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

        object_a = MockedPluginA()


OBJECT_B = MockedPluginB()
