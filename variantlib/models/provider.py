from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from variantlib.constants import VALIDATION_FEATURE_NAME_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PYTHON_PACKAGE_NAME_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.models.base import BaseModel
from variantlib.models.variant import VariantProperty
from variantlib.validators import validate_and
from variantlib.validators import validate_list_all_unique
from variantlib.validators import validate_list_matches_re
from variantlib.validators import validate_list_min_len
from variantlib.validators import validate_matches_re
from variantlib.validators import validate_type

if TYPE_CHECKING:
    from collections.abc import Generator

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@dataclass(frozen=True)
class VariantFeatureConfig(BaseModel):
    name: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, str),
                    lambda v: validate_matches_re(v, VALIDATION_FEATURE_NAME_REGEX),
                ],
                value=val,
            )
        }
    )

    # Acceptable values in priority order
    values: list[str] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[str]),
                    lambda v: validate_list_matches_re(v, VALIDATION_VALUE_REGEX),
                    lambda v: validate_list_min_len(v, 1),
                    lambda v: validate_list_all_unique(v),
                ],
                value=val,
            )
        }
    )

    def __post_init__(self) -> None:
        # Normalization of feature values to lowercase

        # Only "legal way" to modify a frozen dataclass attribute post init.
        if isinstance(self.name, str):
            object.__setattr__(self, "name", self.name.lower())
        if isinstance(self.values, list):
            object.__setattr__(self, "values", [v.lower() for v in self.values])

        # Execute the validator
        super().__post_init__()


@dataclass(frozen=True)
class ProviderConfig(BaseModel):
    namespace: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, str),
                    lambda v: validate_matches_re(v, VALIDATION_NAMESPACE_REGEX),
                ],
                value=val,
            )
        }
    )

    # `VariantFeatureConfigs` in priority order
    configs: list[VariantFeatureConfig] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[VariantFeatureConfig]),
                    lambda v: validate_list_min_len(v, 1),
                    lambda v: validate_list_all_unique(v, keys=["name"]),
                ],
                value=val,
            ),
        }
    )

    def __post_init__(self) -> None:
        # Normalization of feature values to lowercase

        # Only "legal way" to modify a frozen dataclass attribute post init.
        if isinstance(self.namespace, str):
            object.__setattr__(self, "namespace", self.namespace.lower())

        # Execute the validator
        super().__post_init__()

    def pretty_print(self) -> str:
        result_str = f"\n{'#' * 20} Provider Config: `{self.namespace}` {'#' * 20}"
        header_length = len(result_str) - 1

        for kid, vconfig in enumerate(self.configs):
            result_str += (
                f"\n\t- Variant Config [{kid + 1:03d}]: "
                f"{vconfig.name} :: {vconfig.values}"
            )

        result_str += f"\n{'#' * header_length}\n"
        return result_str

    def to_list_of_properties(self) -> Generator[VariantProperty]:
        """Flatten the config into a list of ordered properties"""
        for feat_cfg in self.configs:
            for value in feat_cfg.values:
                yield VariantProperty(self.namespace, feat_cfg.name, value)


@dataclass(frozen=True)
class ProviderPackage(BaseModel):
    namespace: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, str),
                    lambda v: validate_matches_re(v, VALIDATION_NAMESPACE_REGEX),
                ],
                value=val,
            )
        }
    )

    package_name: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, str),
                    lambda v: validate_matches_re(
                        v, VALIDATION_PYTHON_PACKAGE_NAME_REGEX
                    ),
                ],
                value=val,
            )
        }
    )

    def __post_init__(self) -> None:
        # Normalization of feature values to lowercase

        # Only "legal way" to modify a frozen dataclass attribute post init.
        if isinstance(self.namespace, str):
            object.__setattr__(self, "namespace", self.namespace.lower())

        # Execute the validator
        super().__post_init__()

    @classmethod
    def from_str(cls, provider_str: str) -> Self:
        validate_type(provider_str, str)
        input_validation_regex = re.compile(
            rf"({VALIDATION_NAMESPACE_REGEX.pattern})\s*:"
            rf"\s*({VALIDATION_PYTHON_PACKAGE_NAME_REGEX.pattern})",
            re.IGNORECASE,
        )
        validate_matches_re(provider_str, input_validation_regex)

        return cls(*[val.strip() for val in provider_str.split(":")])

    def to_str(self) -> str:
        return f"{self.namespace}: {self.package_name}"
