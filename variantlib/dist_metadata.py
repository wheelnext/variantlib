from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_HASH_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_REQUIRES_HEADER
from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VALIDATION_VARIANT_HASH_REGEX
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.validators import ValidationError
from variantlib.validators import validate_list_matches_re
from variantlib.validators import validate_matches_re

if TYPE_CHECKING:
    from email.message import Message


def get_comma_sep(val: str) -> list[str]:
    if not val.strip():
        return []
    return [x.strip() for x in val.split(",")]


class DistMetadata(VariantMetadata):
    variant_hash: str
    variant_desc: VariantDescription

    def __init__(self, metadata: Message) -> None:
        # TODO: check for duplicate values

        variant_hash = metadata.get(METADATA_VARIANT_HASH_HEADER, "")
        validate_matches_re(
            variant_hash,
            VALIDATION_VARIANT_HASH_REGEX,
            METADATA_VARIANT_HASH_HEADER,
        )
        self.variant_hash = variant_hash

        variant_properties = metadata.get_all(METADATA_VARIANT_PROPERTY_HEADER, [])
        validate_list_matches_re(
            variant_properties,
            VALIDATION_PROPERTY_REGEX,
            METADATA_VARIANT_PROPERTY_HEADER,
        )
        self.variant_desc = VariantDescription(
            [VariantProperty.from_str(x) for x in variant_properties]
        )

        if self.variant_desc.hexdigest != self.variant_hash:
            raise ValidationError(
                f"{METADATA_VARIANT_HASH_HEADER} specifies incorrect hash: "
                f"{variant_hash!r}; expected: {self.variant_desc.hexdigest!r}"
            )

        namespace_priorities = get_comma_sep(
            metadata.get(METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER, "")
        )
        validate_list_matches_re(
            namespace_priorities,
            VALIDATION_NAMESPACE_REGEX,
            METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER,
        )
        self.namespace_priorities = namespace_priorities

        feature_priorities = get_comma_sep(
            metadata.get(METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER, "")
        )
        validate_list_matches_re(
            feature_priorities,
            VALIDATION_FEATURE_REGEX,
            METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER,
        )
        self.feature_priorities = [
            VariantFeature.from_str(x) for x in feature_priorities
        ]

        property_priorities = get_comma_sep(
            metadata.get(METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER, "")
        )
        validate_list_matches_re(
            property_priorities,
            VALIDATION_PROPERTY_REGEX,
            METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER,
        )
        self.property_priorities = [
            VariantProperty.from_str(x) for x in property_priorities
        ]

        provider_requires: dict[str, list[str]] = {}
        for require_tag in metadata.get_all(
            METADATA_VARIANT_PROVIDER_REQUIRES_HEADER, []
        ):
            match = validate_matches_re(
                require_tag,
                VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX,
                METADATA_VARIANT_PROVIDER_REQUIRES_HEADER,
            )
            provider_requires.setdefault(match.group("namespace"), []).append(
                match.group("requirement_str")
            )

        provider_plugin_api: dict[str, str] = {}
        for plugin_api_tag in metadata.get_all(
            METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER, []
        ):
            match = validate_matches_re(
                plugin_api_tag,
                VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX,
                METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER,
            )
            provider_plugin_api[match.group("namespace")] = match.group("plugin_api")

        missing_plugin_api = set(provider_requires) - set(provider_plugin_api)
        if missing_plugin_api:
            raise ValidationError(
                f"{METADATA_VARIANT_PROVIDER_REQUIRES_HEADER} includes namespaces that "
                f"are not included in {METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER}: "
                f"{missing_plugin_api}"
            )

        self.providers = {
            namespace: ProviderInfo(
                requires=provider_requires.get(namespace, []), plugin_api=plugin_api
            )
            for namespace, plugin_api in provider_plugin_api.items()
        }

        if set(self.namespace_priorities) != set(self.providers.keys()):
            raise ValidationError(
                f"{METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER} must specify "
                f"the same namespaces as {METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER} "
                f"key; currently: {set(self.namespace_priorities)} vs. "
                f"{set(self.providers.keys())}"
            )
