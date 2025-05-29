from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
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
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.validators.keytracking import KeyTrackingValidator

# Type Alias to ease type checking
VariantDict = dict[str, dict[str, Any]]

if TYPE_CHECKING:
    from collections.abc import Generator

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@dataclass(init=False)
class VariantsJson(VariantMetadata):
    variants: dict[str, VariantDescription] = field(default_factory=dict)

    def __init__(
        self, variants_json: dict[str, VariantDescription] | VariantMetadata
    ) -> None:
        """Init from pre-read ``variants.json`` data or another class"""

        if isinstance(variants_json, VariantMetadata):
            # Convert from another related class.
            super().__init__(**variants_json.copy_as_kwargs())
            self.variants = {}
            return

        self._process(variants_json)

    @staticmethod
    def _provider_info_to_json(
        provider_info: ProviderInfo,
    ) -> Generator[tuple[str, str | list[str]]]:
        if provider_info.requires:
            yield (VARIANTS_JSON_PROVIDER_REQUIRES_KEY, provider_info.requires)
        if provider_info.enable_if is not None:
            yield (VARIANTS_JSON_PROVIDER_ENABLE_IF_KEY, provider_info.enable_if)
        yield (VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY, provider_info.plugin_api)

    def to_str(self) -> str:
        """Serialize variants.json as a JSON string"""

        data = {
            VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
            VARIANTS_JSON_DEFAULT_PRIO_KEY: {
                VARIANTS_JSON_NAMESPACE_KEY: self.namespace_priorities,
                VARIANTS_JSON_FEATURE_KEY: [
                    x.to_str() for x in self.feature_priorities
                ],
                VARIANTS_JSON_PROPERTY_KEY: [
                    x.to_str() for x in self.property_priorities
                ],
            },
            VARIANTS_JSON_PROVIDER_DATA_KEY: {
                namespace: dict(self._provider_info_to_json(provider_info))
                for namespace, provider_info in self.providers.items()
            },
            VARIANTS_JSON_VARIANT_DATA_KEY: {
                vhash: vdesc.to_dict() for vhash, vdesc in self.variants.items()
            },
        }
        return json.dumps(data, indent=4)

    def merge(self, wheel_metadata: Self) -> None:
        """Merge metadata from another wheel (VariantsJson instance)"""

        # Merge the variant properties
        self.variants.update(wheel_metadata.variants)

        # Verify consistency of default priorities
        for attribute in (
            "namespace_priorities",
            "feature_priorities",
            "property_priorities",
        ):
            new_value = getattr(wheel_metadata, attribute)
            old_value = getattr(self, attribute)
            if old_value != new_value:
                raise ValidationError(
                    f"Inconsistency in {attribute!r} when merging variants. "
                    f"Expected: {old_value!r}, found {new_value!r}"
                )

        for namespace, provider_info in wheel_metadata.providers.items():
            if (old_provider_info := self.providers.get(namespace)) is None:
                # If provider not yet specified, just copy it
                self.providers[namespace] = provider_info
            else:
                # Otherwise, merge requirements and verify consistency
                for req_str in provider_info.requires:
                    if req_str not in old_provider_info.requires:
                        old_provider_info.requires.append(req_str)
                if provider_info.enable_if != old_provider_info.enable_if:
                    raise ValidationError(
                        f"Inconsistency in providers[{namespace!r}].enable_if. "
                        f"Expected: {old_provider_info.enable_if!r}, "
                        f"Found: {provider_info.enable_if!r}"
                    )
                if provider_info.plugin_api != old_provider_info.plugin_api:
                    raise ValidationError(
                        f"Inconsistency in providers[{namespace!r}].plugin_api. "
                        f"Expected: {old_provider_info.plugin_api!r}, "
                        f"Found: {provider_info.plugin_api!r}"
                    )

    def _process(self, variant_table: dict[str, VariantDescription]) -> None:
        validator = KeyTrackingValidator(None, variant_table)

        with validator.get(
            VARIANTS_JSON_VARIANT_DATA_KEY,
            dict[str, VariantDict],
        ) as variants:
            validator.list_matches_re(VALIDATION_VARIANT_HASH_REGEX)
            variant_hashes = list(variants.keys())
            self.variants = {}
            for variant_hash in variant_hashes:
                with validator.get(
                    variant_hash,
                    VariantDict,
                    ignore_subkeys=True,
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
