from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from variantlib.constants import PYPROJECT_TOML_DEFAULT_PRIO_KEY
from variantlib.constants import PYPROJECT_TOML_FEATURE_KEY
from variantlib.constants import PYPROJECT_TOML_NAMESPACE_KEY
from variantlib.constants import PYPROJECT_TOML_PROPERTY_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_DATA_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_REQUIRES_KEY
from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VALIDATION_PROVIDER_ENABLE_IF_REGEX
from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VariantInfoJsonDict
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.validators.keytracking import KeyTrackingValidator

if TYPE_CHECKING:
    from pathlib import Path

if sys.version_info >= (3, 11):
    from typing import Self

    import tomllib
else:
    import tomli as tomllib
    from typing_extensions import Self


@dataclass(init=False)
class VariantPyProjectToml(VariantMetadata):
    def __init__(self, toml_data: dict[str, Any] | VariantMetadata) -> None:
        """Init from pre-read ``pyproject.toml`` data or another class"""

        if isinstance(toml_data, VariantMetadata):
            # Convert from another related class.
            super().__init__(**toml_data.copy_as_kwargs())
            return

        self._process(toml_data.get(PYPROJECT_TOML_TOP_KEY, {}))

    @classmethod
    def from_path(cls, path: Path) -> Self:
        with path.open("rb") as f:
            return cls(tomllib.load(f))

    def _process(self, variant_table: dict[str, VariantInfoJsonDict]) -> None:
        validator = KeyTrackingValidator(PYPROJECT_TOML_TOP_KEY, variant_table)

        with validator.get(PYPROJECT_TOML_DEFAULT_PRIO_KEY, dict[str, Any], {}):
            with validator.get(
                PYPROJECT_TOML_NAMESPACE_KEY, list[str], []
            ) as namespace_priorities:
                validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
                self.namespace_priorities = list(namespace_priorities)
            with validator.get(
                PYPROJECT_TOML_FEATURE_KEY, list[str], []
            ) as feature_priorities:
                validator.list_matches_re(VALIDATION_FEATURE_REGEX)
                self.feature_priorities = [
                    VariantFeature.from_str(x) for x in feature_priorities
                ]
            with validator.get(
                PYPROJECT_TOML_PROPERTY_KEY, list[str], []
            ) as property_priorities:
                validator.list_matches_re(VALIDATION_PROPERTY_REGEX)
                self.property_priorities = [
                    VariantProperty.from_str(x) for x in property_priorities
                ]

        with validator.get(
            PYPROJECT_TOML_PROVIDER_DATA_KEY, dict[str, Any], {}
        ) as providers:
            validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
            namespaces = list(providers.keys())
            self.providers = {}
            for namespace in namespaces:
                with validator.get(namespace, dict[str, Any], {}):
                    with validator.get(
                        PYPROJECT_TOML_PROVIDER_REQUIRES_KEY, list[str], []
                    ) as provider_requires:
                        validator.list_matches_re(VALIDATION_PROVIDER_REQUIRES_REGEX)
                    with validator.get(
                        PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY, str
                    ) as provider_plugin_api:
                        validator.matches_re(VALIDATION_PROVIDER_PLUGIN_API_REGEX)
                    with validator.get(
                        PYPROJECT_TOML_PROVIDER_ENABLE_IF_KEY, str, None
                    ) as provider_enable_if:
                        if provider_enable_if is not None:
                            validator.matches_re(VALIDATION_PROVIDER_ENABLE_IF_REGEX)
                    self.providers[namespace] = ProviderInfo(
                        requires=list(provider_requires),
                        enable_if=provider_enable_if,
                        plugin_api=provider_plugin_api,
                    )

        all_providers = set(self.providers.keys())
        all_providers_key = ".".join(
            [*validator.keys, PYPROJECT_TOML_PROVIDER_DATA_KEY]
        )
        namespace_prios_key = ".".join(
            [
                *validator.keys,
                PYPROJECT_TOML_DEFAULT_PRIO_KEY,
                PYPROJECT_TOML_NAMESPACE_KEY,
            ]
        )
        if set(self.namespace_priorities) != all_providers:
            raise ValidationError(
                f"{namespace_prios_key} must specify the same namespaces "
                f"as {all_providers_key} keys; currently: "
                f"{set(self.namespace_priorities)} vs. {all_providers}"
            )
