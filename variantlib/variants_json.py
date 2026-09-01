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
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_BUILD_REQUIRES_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_FEATURE_ORDER_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_OPTIONAL_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_STATIC_PROPERTIES_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.constants import VariantInfoJsonDict
from variantlib.constants import VariantsJsonDict
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant_info import ProviderInfo
from variantlib.models.variant_info import VariantInfo
from variantlib.validators.keytracking import KeyTrackingValidator

if TYPE_CHECKING:
    from collections.abc import Generator


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
    ) -> Generator[tuple[str, str | list[str] | dict[str, list[str]] | bool]]:
        if provider_info.requires:
            yield (VARIANT_INFO_PROVIDER_REQUIRES_KEY, provider_info.requires)
        if provider_info.enable_if is not None:
            yield (VARIANT_INFO_PROVIDER_ENABLE_IF_KEY, provider_info.enable_if)
        if provider_info.optional:
            yield (VARIANT_INFO_PROVIDER_OPTIONAL_KEY, provider_info.optional)
        if provider_info.plugin_api is not None:
            yield (VARIANT_INFO_PROVIDER_PLUGIN_API_KEY, provider_info.plugin_api)
        if provider_info.static_properties:
            yield (
                VARIANT_INFO_PROVIDER_STATIC_PROPERTIES_KEY,
                provider_info.static_properties,
            )
        if provider_info.feature_order:
            yield (
                VARIANT_INFO_PROVIDER_FEATURE_ORDER_KEY,
                provider_info.feature_order,
            )
        if provider_info.build_requires:
            yield (
                VARIANT_INFO_PROVIDER_BUILD_REQUIRES_KEY,
                provider_info.build_requires,
            )

    def _priorities_to_json(self) -> Generator[tuple[str, Any]]:
        yield (VARIANT_INFO_NAMESPACE_KEY, self.namespace_priorities)

    def providers_dict(
        self,
    ) -> dict[str, dict[str, str | list[str] | dict[str, list[str]] | bool]]:
        """Get a dictionary of providers in a format suitable for JSON serialization"""
        return {
            namespace: dict(self._provider_info_to_json(provider_info))
            for namespace, provider_info in self.providers.items()
        }

    def to_str(self) -> str:
        """Serialize variants.json as a JSON string"""

        assert all(label == vdesc.label for label, vdesc in self.variants.items())

        data: dict[str, Any] = {
            VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
            VARIANT_INFO_DEFAULT_PRIO_KEY: dict(self._priorities_to_json()),
            VARIANT_INFO_PROVIDER_DATA_KEY: self.providers_dict(),
            VARIANTS_JSON_VARIANT_DATA_KEY: {
                vhash: vdesc.to_dict() for vhash, vdesc in self.variants.items()
            },
        }

        return json.dumps(data, indent=4, sort_keys=True)

    def merge(self, variant_dist_info: Self) -> None:
        """Merge info from another wheel (VariantsJson instance)"""

        # Merge the variant properties
        self.variants.update(variant_dist_info.variants)

        # Merge namespace priorities
        # Both lists should start with the same values, the longer one
        # is the result
        namespace_priorities = sorted(
            (self.namespace_priorities, variant_dist_info.namespace_priorities), key=len
        )
        if (
            namespace_priorities[0]
            != namespace_priorities[1][: len(namespace_priorities[0])]
        ):
            raise ValidationError(
                f"Inconsistency in {VARIANT_INFO_DEFAULT_PRIO_KEY}."
                f"{VARIANT_INFO_NAMESPACE_KEY} when merging variants. "
                f"Unable to merge: {namespace_priorities!r}"
            )
        variant_dist_info.namespace_priorities = namespace_priorities[1]

        for namespace, provider_info in variant_dist_info.providers.items():
            if (old_provider_info := self.providers.get(namespace)) is None:
                # If provider not yet specified, just copy it
                self.providers[namespace] = provider_info
            # Otherwise, verify consistency
            elif provider_info != old_provider_info:
                raise ValidationError(
                    f"Inconsistency in providers.{namespace}. "
                    f"Expected: {old_provider_info!r}, found: {provider_info!r}"
                )

    @property
    def _build_requires_allowed(self) -> bool:
        return False

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
                    vdesc = VariantDescription.from_dict(
                        packed_vdesc, label=variant_label
                    )
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
