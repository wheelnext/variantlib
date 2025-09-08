from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.protocols import VariantFeatureConfigType


@dataclass
class VariantFeatureConfig:
    name: str
    values: list[str]
    multi_value: bool = False


namespace = "module_namespace"


def get_all_configs() -> list[VariantFeatureConfigType]:
    return [VariantFeatureConfig("feature", ["a", "b"])]


def get_supported_configs() -> list[VariantFeatureConfigType]:
    return []
