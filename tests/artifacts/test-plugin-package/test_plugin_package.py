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


def get_all_configs(known_properties: frozenset[VariantPropertyType] | None) -> list[FeatConfig]:
    assert known_properties is None
    return [
        FeatConfig("feat1", ["val1a", "val1b", "val1c"]),
        FeatConfig("feat2", ["val2a", "val2b"]),
    ]


def get_supported_configs(known_properties: frozenset[VariantPropertyType] | None) -> list[FeatConfig]:
    assert known_properties is None
    return [
        FeatConfig("feat1", ["val1c", "val1b"]),
    ]
