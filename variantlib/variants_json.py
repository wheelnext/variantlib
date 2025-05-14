from __future__ import annotations

from typing import Any

from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VALIDATION_PROVIDER_ENABLE_IF_REGEX
from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_VARIANT_HASH_REGEX
from variantlib.constants import VARIANTS_JSON_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANTS_JSON_FEATURE_KEY
from variantlib.constants import VARIANTS_JSON_NAMESPACE_KEY
from variantlib.constants import VARIANTS_JSON_PROPERTY_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_DATA_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.validators import KeyTrackingValidator
from variantlib.validators import ValidationError


class VariantsJson(VariantMetadata):
    variants: dict[str, VariantDescription]

    def __init__(self, variants_json: dict | VariantMetadata) -> None:
        """Init from pre-read ``variants.json`` data or another class"""

        if isinstance(variants_json, VariantMetadata):
            # Convert from another related class.
            super().__init__(**variants_json.copy_as_kwargs())
            self.variants = {}
            return

        self._process(variants_json)

    def _process(self, variant_table: dict) -> None:
        validator = KeyTrackingValidator(None, variant_table)

        with validator.get(VARIANTS_JSON_VARIANT_DATA_KEY, dict[str, dict]) as variants:
            validator.list_matches_re(VALIDATION_VARIANT_HASH_REGEX)
            variant_hashes = list(variants.keys())
            self.variants = {}
            for variant_hash in variant_hashes:
                with validator.get(
                    variant_hash, dict[str, dict], ignore_subkeys=True
                ) as packed_vdesc:
                    vdesc = VariantDescription.from_dict(packed_vdesc)
                    if variant_hash != vdesc.hexdigest:
                        raise ValidationError(
                            f"Variant hash mismatch: {variant_hash=!r} != "
                            f"{vdesc.hexdigest=!r}"
                        )
                    self.variants[variant_hash] = vdesc

        with validator.get(VARIANTS_JSON_DEFAULT_PRIO_KEY, dict[str, Any], {}):
            with validator.get(
                VARIANTS_JSON_NAMESPACE_KEY, list[str], []
            ) as namespace_priorities:
                validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
                self.namespace_priorities = list(namespace_priorities)
            with validator.get(
                VARIANTS_JSON_FEATURE_KEY, list[str], []
            ) as feature_priorities:
                validator.list_matches_re(VALIDATION_FEATURE_REGEX)
                self.feature_priorities = [
                    VariantFeature.from_str(x) for x in feature_priorities
                ]
            with validator.get(
                VARIANTS_JSON_PROPERTY_KEY, list[str], []
            ) as property_priorities:
                validator.list_matches_re(VALIDATION_PROPERTY_REGEX)
                self.property_priorities = [
                    VariantProperty.from_str(x) for x in property_priorities
                ]

        with validator.get(
            VARIANTS_JSON_PROVIDER_DATA_KEY, dict[str, Any], {}
        ) as providers:
            validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
            namespaces = list(providers.keys())
            self.providers = {}
            for namespace in namespaces:
                with validator.get(namespace, dict[str, Any], {}):
                    with validator.get(
                        VARIANTS_JSON_PROVIDER_REQUIRES_KEY, list[str], []
                    ) as provider_requires:
                        validator.list_matches_re(VALIDATION_PROVIDER_REQUIRES_REGEX)
                    with validator.get(
                        VARIANTS_JSON_PROVIDER_ENABLE_IF_KEY, str, None
                    ) as provider_enable_if:
                        if provider_enable_if is not None:
                            validator.matches_re(VALIDATION_PROVIDER_ENABLE_IF_REGEX)
                    with validator.get(
                        VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY, str
                    ) as provider_plugin_api:
                        validator.matches_re(VALIDATION_PROVIDER_PLUGIN_API_REGEX)
                    self.providers[namespace] = ProviderInfo(
                        requires=list(provider_requires),
                        enable_if=provider_enable_if,
                        plugin_api=provider_plugin_api,
                    )

        if set(self.namespace_priorities) != set(self.providers.keys()):
            raise ValidationError(
                f"{VARIANTS_JSON_DEFAULT_PRIO_KEY}.{VARIANTS_JSON_NAMESPACE_KEY} "
                "must specify the same namespaces as "
                f"{VARIANTS_JSON_PROVIDER_DATA_KEY} object; currently: "
                f"{set(self.namespace_priorities)} vs. "
                f"{set(self.providers.keys())}"
            )
