from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_VARIANT_HASH_REGEX
from variantlib.constants import VARIANTS_JSON_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANTS_JSON_FEATURE_KEY
from variantlib.constants import VARIANTS_JSON_NAMESPACE_KEY
from variantlib.constants import VARIANTS_JSON_PROPERTY_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_DATA_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.pyproject_toml import ProviderInfo
from variantlib.validators import KeyTrackingValidator
from variantlib.validators import ValidationError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@dataclass(frozen=True)
class VariantsJson:
    namespace_priorities: list[str]
    feature_priorities: list[VariantFeature]
    property_priorities: list[VariantProperty]
    providers: dict[str, ProviderInfo]
    variants: dict[str, VariantDescription]

    @classmethod
    def from_dict(cls, variants_json: dict) -> Self:
        """Init from pre-read ``variants.json`` data"""
        return cls(**cls._process(variants_json))

    @classmethod
    def _process(cls, variant_table: dict) -> dict:
        validator = KeyTrackingValidator(None, variant_table)

        result: dict[str, Any] = {
            "namespace_priorities": [],
            "feature_priorities": [],
            "property_priorities": [],
            "providers": {},
            "variants": {},
        }

        with validator.get(VARIANTS_JSON_VARIANT_DATA_KEY, dict[str, dict]) as variants:
            validator.list_matches_re(VALIDATION_VARIANT_HASH_REGEX)
            variant_hashes = list(variants.keys())
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
                    result["variants"][variant_hash] = vdesc

        with validator.get(VARIANTS_JSON_DEFAULT_PRIO_KEY, dict[str, Any], {}):
            with validator.get(
                VARIANTS_JSON_NAMESPACE_KEY, list[str], []
            ) as namespace_priorities:
                validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
                result["namespace_priorities"] = namespace_priorities
            with validator.get(
                VARIANTS_JSON_FEATURE_KEY, list[str], []
            ) as feature_priorities:
                validator.list_matches_re(VALIDATION_FEATURE_REGEX)
                result["feature_priorities"] = [
                    VariantFeature.from_str(x) for x in feature_priorities
                ]
            with validator.get(
                VARIANTS_JSON_PROPERTY_KEY, list[str], []
            ) as property_priorities:
                validator.list_matches_re(VALIDATION_PROPERTY_REGEX)
                result["property_priorities"] = [
                    VariantProperty.from_str(x) for x in property_priorities
                ]

        with validator.get(
            VARIANTS_JSON_PROVIDER_DATA_KEY, dict[str, Any], {}
        ) as providers:
            validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
            namespaces = list(providers.keys())
            result["providers"] = {}
            for namespace in namespaces:
                with validator.get(namespace, dict[str, Any], {}):
                    with validator.get(
                        VARIANTS_JSON_PROVIDER_REQUIRES_KEY, list[str], []
                    ) as provider_requires:
                        validator.list_matches_re(VALIDATION_PROVIDER_REQUIRES_REGEX)
                    with validator.get(
                        VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY, str, None
                    ) as provider_plugin_api:
                        validator.matches_re(VALIDATION_PROVIDER_PLUGIN_API_REGEX)
                    result["providers"][namespace] = ProviderInfo(
                        provider_requires, provider_plugin_api
                    )

        if set(result["namespace_priorities"]) != set(result["providers"].keys()):
            raise ValidationError(
                f"{VARIANTS_JSON_DEFAULT_PRIO_KEY}.{VARIANTS_JSON_NAMESPACE_KEY} "
                "must specify the same namespaces as "
                f"{VARIANTS_JSON_PROVIDER_DATA_KEY} object; currently: "
                f"{set(result['namespace_priorities'])} vs. "
                f"{set(result['providers'].keys())}"
            )

        return result
