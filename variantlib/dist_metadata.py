from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from variantlib.constants import METADATA_ALL_HEADERS
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_HASH_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_REQUIRES_HEADER
from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_METADATA_PROVIDER_ENABLE_IF_REGEX
from variantlib.constants import VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VALIDATION_VARIANT_HASH_REGEX
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.validators.base import validate_list_matches_re
from variantlib.validators.base import validate_matches_re

if TYPE_CHECKING:
    import sys
    from email.message import Message

    if sys.version_info >= (3, 11):
        pass
    else:
        pass


@dataclass(init=False)
class DistMetadata(VariantMetadata):
    variant_hash: str = "00000000"
    variant_desc: VariantDescription = field(
        default_factory=lambda: VariantDescription([])
    )

    def __init__(self, metadata: Message | VariantMetadata) -> None:
        """Init from distribution metadata or another class"""

        if isinstance(metadata, VariantMetadata):
            # Convert from another related class.
            self.variant_hash = "00000000"
            self.variant_desc = VariantDescription([])
            super().__init__(**metadata.copy_as_kwargs())
            return

        def get_one(key: str) -> str:
            values = metadata.get_all(key, [])
            if len(values) != 1:
                raise ValidationError(
                    f"{key}: found {len(values)} instances of header that is expected "
                    "to occur exactly once"
                )
            return values[0]

        def get_priority_list(key: str) -> list[str]:
            values = metadata.get_all(key, [])
            if len(values) > 1:
                raise ValidationError(
                    f"{key}: found {len(values)} instances of header that is expected "
                    "at most once"
                )
            if not values or not values[0].strip():
                return []
            return [x.strip() for x in values[0].split(",")]

        variant_hash = get_one(METADATA_VARIANT_HASH_HEADER)
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

        namespace_priorities = get_priority_list(
            METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER
        )
        validate_list_matches_re(
            namespace_priorities,
            VALIDATION_NAMESPACE_REGEX,
            METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER,
        )
        self.namespace_priorities = namespace_priorities

        feature_priorities = get_priority_list(
            METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER
        )
        validate_list_matches_re(
            feature_priorities,
            VALIDATION_FEATURE_REGEX,
            METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER,
        )
        self.feature_priorities = [
            VariantFeature.from_str(x) for x in feature_priorities
        ]

        property_priorities = get_priority_list(
            METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER
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

        provider_enable_if: dict[str, str] = {}
        for enable_if_tag in metadata.get_all(
            METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER, []
        ):
            match = validate_matches_re(
                enable_if_tag,
                VALIDATION_METADATA_PROVIDER_ENABLE_IF_REGEX,
                METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER,
            )
            if match.group("namespace") in provider_enable_if:
                raise ValidationError(
                    f"{METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER}: duplicate value "
                    f"for namespace {match.group('namespace')}"
                )
            provider_enable_if[match.group("namespace")] = match.group("enable_if")

        provider_plugin_api: dict[str, str] = {}
        for plugin_api_tag in metadata.get_all(
            METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER, []
        ):
            match = validate_matches_re(
                plugin_api_tag,
                VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX,
                METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER,
            )
            if match.group("namespace") in provider_plugin_api:
                raise ValidationError(
                    f"{METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER}: duplicate value "
                    f"for namespace {match.group('namespace')}"
                )
            provider_plugin_api[match.group("namespace")] = match.group("plugin_api")

        missing_plugin_api = (set(provider_requires) | set(provider_enable_if)) - set(
            provider_plugin_api
        )
        if missing_plugin_api:
            raise ValidationError(
                f"{METADATA_VARIANT_PROVIDER_REQUIRES_HEADER} and "
                f"{METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER} include namespaces that "
                f"are not included in {METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER}: "
                f"{missing_plugin_api}"
            )

        self.providers = {
            namespace: ProviderInfo(
                requires=provider_requires.get(namespace, []),
                enable_if=provider_enable_if.get(namespace),
                plugin_api=plugin_api,
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

    def update_message(self, message: Message) -> None:
        """Update Message with headers from this class"""

        # Remove old metadata
        # NB: del on Message class does not fail if header does not exist
        for key in METADATA_ALL_HEADERS:
            del message[key]

        # Update the hash, in case the user modified variant description
        self.variant_hash = self.variant_desc.hexdigest

        # Set new metadata
        for vprop in self.variant_desc.properties:
            message[METADATA_VARIANT_PROPERTY_HEADER] = vprop.to_str()
        message[METADATA_VARIANT_HASH_HEADER] = self.variant_hash

        for namespace, provider_info in self.providers.items():
            for requirement in provider_info.requires:
                message[METADATA_VARIANT_PROVIDER_REQUIRES_HEADER] = (
                    f"{namespace}: {requirement}"
                )
            if provider_info.enable_if is not None:
                message[METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER] = (
                    f"{namespace}: {provider_info.enable_if}"
                )
            message[METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER] = (
                f"{namespace}: {provider_info.plugin_api}"
            )

        if self.namespace_priorities:
            message[METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER] = ", ".join(
                self.namespace_priorities
            )
        if self.feature_priorities:
            message[METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER] = ", ".join(
                x.to_str() for x in self.feature_priorities
            )
        if self.property_priorities:
            message[METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER] = ", ".join(
                x.to_str() for x in self.property_priorities
            )
