from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from variantlib.models.variant import VariantFeature
    from variantlib.models.variant import VariantProperty


@dataclass
class ProviderInfo:
    plugin_api: str
    enable_if: str | None = None
    requires: list[str] = field(default_factory=list)


@dataclass
class VariantMetadata:
    namespace_priorities: list[str] = field(default_factory=list)
    feature_priorities: list[VariantFeature] = field(default_factory=list)
    property_priorities: list[VariantProperty] = field(default_factory=list)
    providers: dict[str, ProviderInfo] = field(default_factory=dict)

    def copy_as_kwargs(self) -> dict[str, Any]:
        """Return a "kwargs" dict suitable for instantiating a copy of itself"""

        return {
            "namespace_priorities": list(self.namespace_priorities),
            "feature_priorities": list(self.feature_priorities),
            "property_priorities": list(self.property_priorities),
            "providers": {
                namespace: ProviderInfo(
                    requires=list(provider_data.requires),
                    enable_if=provider_data.enable_if,
                    plugin_api=provider_data.plugin_api,
                )
                for namespace, provider_data in self.providers.items()
            },
        }

    def get_provider_requires(self, namespaces: set[str] | None = None) -> set[str]:
        """
        Get list of requirements for providers in metadata

        If `namespaces` is not None, only requirements for given namespaces
        will be returned. Otherwise, all requirements will be returned.
        """

        if namespaces is None:
            namespaces = set(self.namespace_priorities)

        requirements = set()
        for namespace in namespaces:
            requirements.update(self.providers[namespace].requires)
        return requirements
