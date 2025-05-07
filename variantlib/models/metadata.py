from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.models.variant import VariantFeature
    from variantlib.models.variant import VariantProperty


@dataclass
class ProviderInfo:
    requires: list[str]
    plugin_api: str


@dataclass
class VariantMetadata:
    namespace_priorities: list[str]
    feature_priorities: list[VariantFeature]
    property_priorities: list[VariantProperty]
    providers: dict[str, ProviderInfo]
