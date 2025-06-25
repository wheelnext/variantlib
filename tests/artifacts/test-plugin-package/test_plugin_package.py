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
dynamic = False


def validate_properties(
    properties: frozenset[VariantPropertyType],
) -> dict[VariantPropertyType, bool]:
    assert all(prop.namespace == namespace for prop in properties)
    return {
        prop: (prop.feature == "feat1" and prop.value in ["val1a", "val1b", "val1c"])
        or (prop.feature == "feat2" and prop.value in ["val2a", "val2b"])
        for prop in properties
    }


def get_supported_configs(
    known_properties: frozenset[VariantPropertyType] | None,
) -> list[FeatConfig]:
    assert known_properties is None
    return [
        FeatConfig("feat1", ["val1c", "val1b"]),
    ]
