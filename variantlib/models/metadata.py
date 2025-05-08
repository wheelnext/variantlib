from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.models.variant import VariantFeature
    from variantlib.models.variant import VariantProperty


@dataclass
class ProviderInfo:
    plugin_api: str
    requires: list[str] = field(default_factory=list)


@dataclass
class VariantMetadata:
    namespace_priorities: list[str] = field(default_factory=list)
    feature_priorities: list[VariantFeature] = field(default_factory=list)
    property_priorities: list[VariantProperty] = field(default_factory=list)
    providers: dict[str, ProviderInfo] = field(default_factory=dict)
