from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.constants import VariantInfoJsonDict
from variantlib.models.variant_info import VariantInfo
from variantlib.validators.keytracking import KeyTrackingValidator

if TYPE_CHECKING:
    from pathlib import Path

    from variantlib.protocols import VariantNamespace

if sys.version_info >= (3, 11):
    from typing import Self

    import tomllib
else:
    import tomli as tomllib
    from typing_extensions import Self


@dataclass(init=False)
class VariantPyProjectToml(VariantInfo):
    def __init__(self, toml_data: dict[str, Any] | VariantInfo) -> None:
        """Init from pre-read ``pyproject.toml`` data or another class"""

        if isinstance(toml_data, VariantInfo):
            # Convert from another related class.
            super().__init__(**toml_data.copy_as_kwargs())
            return

        self._process(toml_data.get(PYPROJECT_TOML_TOP_KEY, {}))

    @classmethod
    def from_path(cls, path: Path) -> Self:
        with path.open("rb") as f:
            return cls(tomllib.load(f))

    def _get_expected_aot_namespaces(self) -> set[VariantNamespace]:
        return {
            namespace
            for namespace, provider_info in self.providers.items()
            if not provider_info.install_time and not provider_info.requires
        }

    def _process(self, variant_table: dict[str, VariantInfoJsonDict]) -> None:
        validator = KeyTrackingValidator(PYPROJECT_TOML_TOP_KEY, variant_table)
        self._process_common(validator)
