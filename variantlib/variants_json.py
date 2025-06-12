from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from variantlib.constants import VALIDATION_VARIANT_HASH_REGEX
from variantlib.constants import VARIANT_METADATA_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_METADATA_FEATURE_KEY
from variantlib.constants import VARIANT_METADATA_NAMESPACE_KEY
from variantlib.constants import VARIANT_METADATA_PROPERTY_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_METADATA_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.constants import VariantInfoJsonDict
from variantlib.constants import VariantsJsonDict
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantInfo
from variantlib.models.variant import VariantDescription
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
    ) -> Generator[tuple[str, str | list[str]]]:
        if provider_info.requires:
            yield (VARIANT_METADATA_PROVIDER_REQUIRES_KEY, provider_info.requires)
        if provider_info.enable_if is not None:
            yield (VARIANT_METADATA_PROVIDER_ENABLE_IF_KEY, provider_info.enable_if)
        if provider_info.plugin_api is not None:
            yield (VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY, provider_info.plugin_api)

    def to_str(self) -> str:
        """Serialize variants.json as a JSON string"""

        data = {
            VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
            VARIANT_METADATA_DEFAULT_PRIO_KEY: {
                VARIANT_METADATA_NAMESPACE_KEY: self.namespace_priorities,
                VARIANT_METADATA_FEATURE_KEY: self.feature_priorities,
                VARIANT_METADATA_PROPERTY_KEY: self.property_priorities,
            },
            VARIANT_METADATA_PROVIDER_DATA_KEY: {
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

    def _process(self, variant_table: VariantsJsonDict) -> None:
        validator = KeyTrackingValidator(None, variant_table)  # type: ignore[arg-type]
        self._process_common_metadata(validator)

        with validator.get(
            VARIANTS_JSON_VARIANT_DATA_KEY,
            dict[str, VariantInfoJsonDict],
        ) as variants:
            validator.list_matches_re(VALIDATION_VARIANT_HASH_REGEX)
            variant_hashes = list(variants.keys())
            self.variants = {}
            for variant_hash in variant_hashes:
                with validator.get(
                    variant_hash,
                    VariantInfoJsonDict,
                    ignore_subkeys=True,
                ) as packed_vdesc:
                    vdesc = VariantDescription.from_dict(packed_vdesc)
                    if variant_hash != vdesc.hexdigest:
                        raise ValidationError(
                            f"Variant hash mismatch: {variant_hash=!r} != "
                            f"{vdesc.hexdigest=!r}"
                        )
                    self.variants[variant_hash] = vdesc
