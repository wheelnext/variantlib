from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any

from packaging.requirements import Requirement

from variantlib.constants import VALIDATION_FEATURE_NAME_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROVIDER_ENABLE_IF_REGEX
from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANT_METADATA_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_METADATA_FEATURE_KEY
from variantlib.constants import VARIANT_METADATA_NAMESPACE_KEY
from variantlib.constants import VARIANT_METADATA_PROPERTY_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_REQUIRES_KEY
from variantlib.errors import ValidationError
from variantlib.protocols import VariantFeatureName
from variantlib.protocols import VariantFeatureValue
from variantlib.protocols import VariantNamespace

if TYPE_CHECKING:
    from variantlib.validators.keytracking import KeyTrackingValidator


@dataclass
class ProviderInfo:
    plugin_api: str | None = None
    enable_if: str | None = None
    requires: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.plugin_api is None and not self.requires:
            raise ValidationError("Either plugin-api or requires need to be specified")

    @property
    def object_reference(self) -> str:
        """Get effective object reference from plugin-api or requires"""
        if self.plugin_api is not None:
            return self.plugin_api
        # TODO: how far should we normalize it?
        return Requirement(self.requires[0]).name.replace("-", "_")


@dataclass
class VariantMetadata:
    namespace_priorities: list[VariantNamespace] = field(default_factory=list)
    feature_priorities: dict[VariantNamespace, list[VariantFeatureName]] = field(
        default_factory=dict
    )
    property_priorities: dict[
        VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
    ] = field(default_factory=dict)
    providers: dict[VariantNamespace, ProviderInfo] = field(default_factory=dict)

    def copy_as_kwargs(self) -> dict[str, Any]:
        """Return a "kwargs" dict suitable for instantiating a copy of itself"""

        return {
            "namespace_priorities": list(self.namespace_priorities),
            "feature_priorities": {
                namespace: list(feature_priorities)
                for namespace, feature_priorities in self.feature_priorities.items()
            },
            "property_priorities": {
                namespace: {
                    feature: list(property_priorities)
                    for feature, property_priorities in feature_dict.items()
                }
                for namespace, feature_dict in self.property_priorities.items()
            },
            "providers": {
                namespace: ProviderInfo(
                    requires=list(provider_data.requires),
                    enable_if=provider_data.enable_if,
                    plugin_api=provider_data.plugin_api,
                )
                for namespace, provider_data in self.providers.items()
            },
        }

    def get_provider_requires(
        self, namespaces: set[VariantNamespace] | None = None
    ) -> set[str]:
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

    def _process_common_metadata(self, validator: KeyTrackingValidator) -> None:
        with validator.get(VARIANT_METADATA_DEFAULT_PRIO_KEY, dict[str, Any], {}):
            with validator.get(
                VARIANT_METADATA_NAMESPACE_KEY, list[VariantNamespace], []
            ) as namespace_priorities:
                validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
                self.namespace_priorities = list(namespace_priorities)
            with validator.get(
                VARIANT_METADATA_FEATURE_KEY,
                dict[VariantNamespace, list[VariantFeatureName]],
                {},
            ) as feature_priorities_dict:
                validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
                self.feature_priorities = {}
                for namespace in feature_priorities_dict:
                    with validator.get(
                        namespace, list[VariantFeatureName]
                    ) as feature_priorities:
                        validator.list_matches_re(VALIDATION_FEATURE_NAME_REGEX)
                        self.feature_priorities[namespace] = feature_priorities
            with validator.get(
                VARIANT_METADATA_PROPERTY_KEY,
                dict[
                    VariantNamespace,
                    dict[VariantFeatureName, list[VariantFeatureValue]],
                ],
                {},
            ) as property_priorities_dict:
                validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
                self.property_priorities = {}
                for namespace in property_priorities_dict:
                    with validator.get(
                        namespace, dict[VariantFeatureName, list[VariantFeatureValue]]
                    ) as feature_dict:
                        validator.list_matches_re(VALIDATION_FEATURE_NAME_REGEX)
                        for feature_name in feature_dict:
                            with validator.get(
                                feature_name, list[VariantFeatureValue]
                            ) as value_priorities:
                                validator.list_matches_re(VALIDATION_VALUE_REGEX)
                                self.property_priorities.setdefault(namespace, {})[
                                    feature_name
                                ] = value_priorities

        with validator.get(
            VARIANT_METADATA_PROVIDER_DATA_KEY, dict[str, Any], {}
        ) as providers:
            validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
            namespaces = list(providers.keys())
            self.providers = {}
            for namespace in namespaces:
                with validator.get(namespace, dict[str, Any], {}):
                    with validator.get(
                        VARIANT_METADATA_PROVIDER_REQUIRES_KEY, list[str], []
                    ) as provider_requires:
                        validator.list_matches_re(VALIDATION_PROVIDER_REQUIRES_REGEX)
                    with validator.get(
                        VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY, str, None
                    ) as provider_plugin_api:
                        if provider_plugin_api is not None:
                            validator.matches_re(VALIDATION_PROVIDER_PLUGIN_API_REGEX)
                    with validator.get(
                        VARIANT_METADATA_PROVIDER_ENABLE_IF_KEY, str, None
                    ) as provider_enable_if:
                        if provider_enable_if is not None:
                            validator.matches_re(VALIDATION_PROVIDER_ENABLE_IF_REGEX)
                    if provider_plugin_api is None and not provider_requires:
                        raise ValidationError(
                            f"{validator.key}: either "
                            f"{VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY} or "
                            f"{VARIANT_METADATA_PROVIDER_REQUIRES_KEY} must be "
                            "specified"
                        )
                    self.providers[namespace] = ProviderInfo(
                        requires=list(provider_requires),
                        enable_if=provider_enable_if,
                        plugin_api=provider_plugin_api,
                    )

        all_providers = set(self.providers.keys())
        all_providers_key = ".".join(
            [*validator.keys, VARIANT_METADATA_PROVIDER_DATA_KEY]
        )
        namespace_prios_key = ".".join(
            [
                *validator.keys,
                VARIANT_METADATA_DEFAULT_PRIO_KEY,
                VARIANT_METADATA_NAMESPACE_KEY,
            ]
        )
        if set(self.namespace_priorities) != all_providers:
            raise ValidationError(
                f"{namespace_prios_key} must specify the same namespaces "
                f"as {all_providers_key} keys; currently: "
                f"{set(self.namespace_priorities)} vs. {all_providers}"
            )
