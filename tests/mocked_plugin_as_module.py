from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.protocols import VariantFeatureConfigType
    from variantlib.protocols import VariantPropertyType


namespace = "module_namespace"
dynamic = False


def validate_properties(
    properties: frozenset[VariantPropertyType],
) -> dict[VariantPropertyType, bool]:
    assert all(prop.namespace == namespace for prop in properties)
    return {
        prop: (prop.feature == "feature" and prop.value in ["a", "b"])
        for prop in properties
    }


def get_supported_configs(
    known_properties: frozenset[VariantPropertyType] | None,
) -> list[VariantFeatureConfigType]:
    assert known_properties is None
    return []
