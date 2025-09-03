from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any

from variantlib.constants import NULL_VARIANT_LABEL
from variantlib.constants import VALIDATION_VARIANT_LABEL_REGEX
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_FEATURE_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROPERTY_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_OPTIONAL_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.constants import VariantInfoJsonDict
from variantlib.constants import VariantsJsonDict
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant_info import PluginUse
from variantlib.models.variant_info import ProviderInfo
from variantlib.models.variant_info import VariantInfo
from variantlib.validators.keytracking import KeyTrackingValidator

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.models.variant import VariantProperty

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@dataclass(init=False)
class VariantsJson(VariantInfo):
    variants: dict[str, VariantDescription] = field(default_factory=dict)

    def __init__(self, variants_json: VariantsJsonDict | VariantInfo) -> None:
        """Init from pre-read ``variants.json`` data or another class"""

        if isinstance(variants_json, VariantInfo):
            # Convert from another related class.
            super().__init__(**variants_json.copy_as_kwargs())
            self.variants = {}
            return

        self._process(variants_json)

    @staticmethod
    def _provider_info_to_json(
        provider_info: ProviderInfo,
    ) -> Generator[tuple[str, str | list[str] | bool]]:
        if provider_info.requires:
            yield (VARIANT_INFO_PROVIDER_REQUIRES_KEY, provider_info.requires)
        if provider_info.enable_if is not None:
            yield (VARIANT_INFO_PROVIDER_ENABLE_IF_KEY, provider_info.enable_if)
        if provider_info.optional:
            yield (VARIANT_INFO_PROVIDER_OPTIONAL_KEY, provider_info.optional)
        if provider_info.plugin_api is not None:
            yield (VARIANT_INFO_PROVIDER_PLUGIN_API_KEY, provider_info.plugin_api)
        if provider_info.plugin_use != PluginUse.ALL:
            yield (VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY, provider_info.plugin_use)

    def _priorities_to_json(self) -> Generator[tuple[str, Any]]:
        yield (VARIANT_INFO_NAMESPACE_KEY, self.namespace_priorities)
        if self.feature_priorities:
            yield (VARIANT_INFO_FEATURE_KEY, self.feature_priorities)
        if self.property_priorities:
            yield (VARIANT_INFO_PROPERTY_KEY, self.property_priorities)

    def providers_dict(self) -> dict[str, dict[str, str | list[str] | bool]]:
        """Get a dictionary of providers in a format suitable for JSON serialization"""
        return {
            namespace: dict(self._provider_info_to_json(provider_info))
            for namespace, provider_info in self.providers.items()
        }

    def to_str(self) -> str:
        """Serialize variants.json as a JSON string"""

        data: dict[str, Any] = {
            VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
            VARIANT_INFO_DEFAULT_PRIO_KEY: dict(self._priorities_to_json()),
            VARIANT_INFO_PROVIDER_DATA_KEY: self.providers_dict(),
            VARIANTS_JSON_VARIANT_DATA_KEY: {
                vhash: vdesc.to_dict() for vhash, vdesc in self.variants.items()
            },
        }

        return json.dumps(data, indent=4, sort_keys=True)

    @property
    def provider_hash(self) -> int:
        encoded_dict = json.dumps(self.providers_dict(), sort_keys=True).encode("utf-8")

        return hash(encoded_dict)

    def merge(self, variant_dist_info: Self) -> None:
        """Merge info from another wheel (VariantsJson instance)"""

        # Merge the variant properties
        self.variants.update(variant_dist_info.variants)

        # Verify consistency of default priorities
        for attribute in (
            "namespace_priorities",
            "feature_priorities",
            "property_priorities",
        ):
            new_value = getattr(variant_dist_info, attribute)
            old_value = getattr(self, attribute)
            if old_value != new_value:
                raise ValidationError(
                    f"Inconsistency in {attribute!r} when merging variants. "
                    f"Expected: {old_value!r}, found {new_value!r}"
                )

        if self.provider_hash != variant_dist_info.provider_hash:
            raise ValidationError(
                f"Inconsistency in providers when merging variants:\n"
                f"Before:\n{self.providers}.\n\nAfter:\n{variant_dist_info.providers}."
            )

        for namespace, provider_info in variant_dist_info.providers.items():
            if (old_provider_info := self.providers.get(namespace)) is None:
                # If provider not yet specified, just copy it
                self.providers[namespace] = provider_info

            else:
                # Otherwise, merge requirements and verify consistency
                for req_str in provider_info.requires:
                    if req_str not in old_provider_info.requires:
                        old_provider_info.requires.append(req_str)
                for attribute in ("enable_if", "optional", "plugin_api"):
                    new = getattr(provider_info, attribute)
                    old = getattr(old_provider_info, attribute)
                    if new != old:
                        raise ValidationError(
                            f"Inconsistency in providers[{namespace!r}].{attribute}. "
                            f"Expected: {old!r}, found: {new!r}"
                        )

    def get_known_properties(self) -> set[VariantProperty]:
        """Get a set of all property values found in listed variants"""
        return {vprop for vdesc in self.variants.values() for vprop in vdesc.properties}

    def _process(self, variant_table: VariantsJsonDict) -> None:
        validator = KeyTrackingValidator(None, variant_table)  # type: ignore[arg-type]
        self._process_common(validator)

        with validator.get(
            VARIANTS_JSON_VARIANT_DATA_KEY,
            dict[str, VariantInfoJsonDict],
        ) as variants:
            validator.list_matches_re(VALIDATION_VARIANT_LABEL_REGEX)
            variant_labels = list(variants.keys())
            self.variants = {}

            for variant_label in variant_labels:
                with validator.get(
                    variant_label,
                    VariantInfoJsonDict,
                    ignore_subkeys=True,
                ) as packed_vdesc:
                    vdesc = VariantDescription.from_dict(packed_vdesc)
                    if vdesc.is_null_variant() and variant_label != NULL_VARIANT_LABEL:
                        raise ValidationError(
                            f"Null variant must use {NULL_VARIANT_LABEL!r} label"
                        )
                    if (
                        not vdesc.is_null_variant()
                        and variant_label == NULL_VARIANT_LABEL
                    ):
                        raise ValidationError(
                            f"{NULL_VARIANT_LABEL!r} label can only be used for "
                            "the null variant"
                        )
                    self.variants[variant_label] = vdesc
