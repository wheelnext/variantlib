from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.protocols import VariantFeatureConfigType
    from variantlib.protocols import VariantPropertyType


namespace = "module_namespace"


def validate_property(
    variant_property: VariantPropertyType,
) -> bool:
    assert variant_property.namespace == namespace
    return variant_property.feature == "feature" and variant_property.value in [
        "a",
        "b",
    ]


def get_supported_configs() -> list[VariantFeatureConfigType]:
    return []
