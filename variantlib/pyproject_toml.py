from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from typing import Any

from variantlib.constants import PYPROJECT_TOML_DEFAULT_PRIO_KEY
from variantlib.constants import PYPROJECT_TOML_FEATURE_KEY
from variantlib.constants import PYPROJECT_TOML_NAMESPACE_KEY
from variantlib.constants import PYPROJECT_TOML_PROPERTY_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_DATA_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_REQUIRES_KEY
from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VALIDATION_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_PROVIDER_REQUIRES_REGEX
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.validators import KeyTrackingValidator
from variantlib.validators import ValidationError

if TYPE_CHECKING:
    from pathlib import Path

if sys.version_info >= (3, 11):
    from typing import Self

    import tomllib
else:
    import tomli as tomllib
    from typing_extensions import Self


class VariantPyProjectToml(VariantMetadata):
    def __init__(self, toml_data: dict) -> None:
        """Init from pre-read ``pyproject.toml`` data"""
        self._process(toml_data.get(PYPROJECT_TOML_TOP_KEY, {}))

    @classmethod
    def from_path(cls, path: Path) -> Self:
        with path.open("rb") as f:
            return cls(tomllib.load(f))

    def _process(self, variant_table: dict) -> None:
        validator = KeyTrackingValidator(PYPROJECT_TOML_TOP_KEY, variant_table)

        with validator.get(PYPROJECT_TOML_DEFAULT_PRIO_KEY, dict[str, Any], {}):
            with validator.get(
                PYPROJECT_TOML_NAMESPACE_KEY, list[str], []
            ) as namespace_priorities:
                validator.list_matches_re(VALIDATION_NAMESPACE_REGEX)
                self.namespace_priorities = namespace_priorities
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
                    self.providers[namespace] = ProviderInfo(
                        provider_requires, provider_plugin_api
                    )

        if set(self.namespace_priorities) != set(self.providers.keys()):
            raise ValidationError(
                f"{PYPROJECT_TOML_TOP_KEY}.{PYPROJECT_TOML_DEFAULT_PRIO_KEY}."
                f"{PYPROJECT_TOML_NAMESPACE_KEY} must specify the same namespaces "
                f"as {PYPROJECT_TOML_TOP_KEY}.{PYPROJECT_TOML_PROVIDER_DATA_KEY} "
                f"table; currently: {set(self.namespace_priorities)} vs. "
                f"{set(self.providers.keys())}"
            )
