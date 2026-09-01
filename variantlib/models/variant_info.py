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
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_BUILD_REQUIRES_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_FEATURE_ORDER_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_OPTIONAL_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_STATIC_PROPERTIES_KEY
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
    optional: bool = False
    requires: list[str] = field(default_factory=list)
    static_properties: dict[VariantFeatureName, list[VariantFeatureValue]] = field(
        default_factory=dict
    )
    feature_order: list[VariantFeatureName] = field(default_factory=list)
    build_requires: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if (
            bool(self.build_requires),
            bool(self.requires),
            bool(self.static_properties),
        ).count(True) != 1:
            raise ValidationError(
                "Exactly one of build_requires, requires and static_properties "
                "must be provided"
            )
        if self.static_properties and self.plugin_api:
            raise ValidationError("plugin_api is invalid with static_properties")
        if not self.static_properties and self.feature_order:
            raise ValidationError("feature_order requires static_properties")

    @property
    def object_reference(self) -> str:
        """Get effective object reference from plugin-api or requires"""
        requires = self.requires or self.build_requires
        assert requires
        if self.plugin_api is not None:
            return self.plugin_api
        return Requirement(requires[0]).name.replace("-", "_")


@dataclass
class VariantInfo:
    namespace_priorities: list[VariantNamespace] = field(default_factory=list)

    providers: dict[VariantNamespace, ProviderInfo] = field(default_factory=dict)

    def copy_as_kwargs(self) -> dict[str, Any]:
        """Return a "kwargs" dict suitable for instantiating a copy of itself"""

        return {
            "namespace_priorities": list(self.namespace_priorities),
            "providers": {
                namespace: ProviderInfo(
                    enable_if=provider_data.enable_if,
                    optional=provider_data.optional,
                    plugin_api=provider_data.plugin_api,
                    requires=list(provider_data.requires),
                    static_properties={
                        feature: list(values)
                        for feature, values in provider_data.static_properties.items()
                    },
                    feature_order=list(provider_data.feature_order),
                    build_requires=list(provider_data.build_requires),
                )
                for namespace, provider_data in self.providers.items()
            },
        }

    def get_provider_requires(
        self,
        namespaces: set[VariantNamespace] | None = None,
        include_aot_plugins: bool = True,
    ) -> set[str]:
        """
        Get list of requirements for providers in variant info

        If `namespaces` is not None, only requirements for given namespaces
        will be returned. Otherwise, all requirements will be returned.
        """

        if namespaces is None:
            namespaces = set(self.namespace_priorities)

        requirements = set()
        for namespace in namespaces:
            provider = self.providers[namespace]
            # requires and build_requires are mutually exclusive,
            # one of them will always be empty
            requirements.update(provider.requires)
            if include_aot_plugins:
                requirements.update(provider.build_requires)
        return requirements

    @property
    def _build_requires_allowed(self) -> bool:
        raise NotImplementedError

    def _process_common(self, validator: KeyTrackingValidator) -> None:
        with (
            validator.get(VARIANT_INFO_DEFAULT_PRIO_KEY, dict[str, Any], {}),
            validator.get(
                VARIANT_INFO_NAMESPACE_KEY, list[VariantNamespace], []
            ) as namespace_priorities,
        ):
            validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
            self.namespace_priorities = list(namespace_priorities)

        with validator.get(
            VARIANT_INFO_PROVIDER_DATA_KEY, dict[str, Any], {}
        ) as providers:
            validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
            namespaces = list(providers.keys())
            self.providers = {}
            for namespace in namespaces:
                with validator.get(namespace, dict[str, Any], {}):
                    with validator.get(
                        VARIANT_INFO_PROVIDER_REQUIRES_KEY, list[str], []
                    ) as provider_requires:
                        validator.list_matches_re(VALIDATION_PROVIDER_REQUIRES_REGEX)
                    with validator.get(
                        VARIANT_INFO_PROVIDER_OPTIONAL_KEY, bool, False
                    ) as provider_optional:
                        pass
                    with validator.get(
                        VARIANT_INFO_PROVIDER_PLUGIN_API_KEY, str, None
                    ) as provider_plugin_api:
                        if provider_plugin_api is not None:
                            validator.matches_re(VALIDATION_PROVIDER_PLUGIN_API_REGEX)
                    with validator.get(
                        VARIANT_INFO_PROVIDER_ENABLE_IF_KEY, str, None
                    ) as provider_enable_if:
                        if provider_enable_if is not None:
                            validator.matches_re(VALIDATION_PROVIDER_ENABLE_IF_REGEX)
                    with validator.get(
                        VARIANT_INFO_PROVIDER_FEATURE_ORDER_KEY,
                        list[VariantFeatureName],
                        [],
                    ) as provider_feature_order:
                        validator.list_matches_re(VALIDATION_FEATURE_NAME_REGEX)
                    with validator.get(
                        VARIANT_INFO_PROVIDER_BUILD_REQUIRES_KEY, list[str], []
                    ) as provider_build_requires:
                        validator.list_matches_re(VALIDATION_PROVIDER_REQUIRES_REGEX)
                    provider_static_properties = {}
                    with validator.get(
                        VARIANT_INFO_PROVIDER_STATIC_PROPERTIES_KEY,
                        dict[VariantFeatureName, list[VariantFeatureValue]],
                        {},
                    ) as feature_dict:
                        validator.list_matches_re(VALIDATION_FEATURE_NAME_REGEX)
                        for feature_name in feature_dict:
                            with validator.get(
                                feature_name, list[VariantFeatureValue]
                            ) as feature_values:
                                validator.list_matches_re(VALIDATION_VALUE_REGEX)
                                provider_static_properties[feature_name] = (
                                    feature_values
                                )

                        if len(feature_dict) > 1:
                            feature_prios = set(provider_feature_order)
                            missing_feature_prios = (
                                set(feature_dict.keys()) - feature_prios
                            )
                            if missing_feature_prios:
                                raise ValidationError(
                                    f"{validator.key}: multiple features require "
                                    "specifying ordering via "
                                    f"{VARIANT_INFO_PROVIDER_FEATURE_ORDER_KEY}; "
                                    f"missing: {missing_feature_prios}"
                                )

                    if provider_build_requires and not self._build_requires_allowed:
                        raise ValidationError(
                            f"{validator.key}: "
                            f"{VARIANT_INFO_PROVIDER_BUILD_REQUIRES_KEY} is not "
                            f"allowed in this file"
                        )
                    if (
                        bool(provider_build_requires),
                        bool(provider_requires),
                        bool(provider_static_properties),
                    ).count(True) != 1:
                        raise ValidationError(
                            f"{validator.key}: exactly one of "
                            f"{VARIANT_INFO_PROVIDER_REQUIRES_KEY}, "
                            f"{VARIANT_INFO_PROVIDER_STATIC_PROPERTIES_KEY} "
                            f"or {VARIANT_INFO_PROVIDER_BUILD_REQUIRES_KEY} "
                            "must be specified"
                        )
                    if provider_static_properties and provider_plugin_api:
                        raise ValidationError(
                            f"{validator.key}: "
                            f"{VARIANT_INFO_PROVIDER_PLUGIN_API_KEY} is not valid "
                            f"with {VARIANT_INFO_PROVIDER_STATIC_PROPERTIES_KEY}"
                        )
                    if not provider_static_properties and provider_feature_order:
                        raise ValidationError(
                            f"{validator.key}: "
                            f"{VARIANT_INFO_PROVIDER_FEATURE_ORDER_KEY} is valid "
                            f"only with {VARIANT_INFO_PROVIDER_STATIC_PROPERTIES_KEY}"
                        )

                    self.providers[namespace] = ProviderInfo(
                        enable_if=provider_enable_if,
                        optional=provider_optional,
                        plugin_api=provider_plugin_api,
                        requires=list(provider_requires),
                        static_properties=provider_static_properties,
                        feature_order=provider_feature_order,
                        build_requires=provider_build_requires,
                    )

        all_providers = set(self.providers.keys())
        all_providers_key = ".".join([*validator.keys, VARIANT_INFO_PROVIDER_DATA_KEY])
        namespace_prios_key = ".".join(
            [
                *validator.keys,
                VARIANT_INFO_DEFAULT_PRIO_KEY,
                VARIANT_INFO_NAMESPACE_KEY,
            ]
        )

        if set(self.namespace_priorities) != all_providers:
            raise ValidationError(
                f"{namespace_prios_key} must specify the same namespaces "
                f"as {all_providers_key} keys; currently: "
                f"{set(self.namespace_priorities)} vs. {all_providers}"
            )
