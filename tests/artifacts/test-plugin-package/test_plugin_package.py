from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.protocols import VariantPropertyType


@dataclass
class FeatConfig:
    name: str
    values: list[str]


namespace = "installable_plugin"


def validate_property(
    variant_property: VariantPropertyType,
) -> bool:
    assert variant_property.namespace == namespace
    return (
        (variant_property.feature == "feat1" and variant_property.value in ["val1a", "val1b", "val1c"])
        or (variant_property.feature == "feat2" and variant_property.value in ["val2a", "val2b"])
        )


def get_supported_configs(
    known_properties: frozenset[VariantPropertyType] | None,
) -> list[FeatConfig]:
    assert known_properties is None
    return [
        FeatConfig("feat1", ["val1c", "val1b"]),
    ]
