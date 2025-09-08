from __future__ import annotations

import sys
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from variantlib.constants import VALIDATION_FEATURE_NAME_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.models.base import BaseModel
from variantlib.models.variant import VariantProperty
from variantlib.protocols import VariantFeatureName
from variantlib.protocols import VariantFeatureValue
from variantlib.protocols import VariantNamespace
from variantlib.validators.base import validate_list_all_unique
from variantlib.validators.base import validate_list_matches_re
from variantlib.validators.base import validate_list_min_len
from variantlib.validators.base import validate_matches_re
from variantlib.validators.base import validate_type
from variantlib.validators.combining import validate_and

if TYPE_CHECKING:
    from collections.abc import Generator

if sys.version_info >= (3, 11):
    pass
else:
    pass


@dataclass(frozen=True)
class VariantFeatureConfig(BaseModel):
    name: VariantFeatureName = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, VariantFeatureName),
                    lambda v: validate_matches_re(v, VALIDATION_FEATURE_NAME_REGEX),  # pyright: ignore[reportArgumentType]
                ],
                value=val,
            )
        }
    )

    # Acceptable values in priority order
    values: list[VariantFeatureValue] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[VariantFeatureValue]),
                    lambda v: validate_list_matches_re(v, VALIDATION_VALUE_REGEX),  # pyright: ignore[reportArgumentType]
                    lambda v: validate_list_min_len(v, 1),  # pyright: ignore[reportArgumentType]
                    lambda v: validate_list_all_unique(v),  # pyright: ignore[reportArgumentType]
                ],
                value=val,
            )
        }
    )

    multi_value: bool = False


@dataclass(frozen=True)
class ProviderConfig(BaseModel):
    namespace: VariantNamespace = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, VariantNamespace),
                    lambda v: validate_matches_re(v, VALIDATION_NAMESPACE_REGEX),  # pyright: ignore[reportArgumentType]
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
                    lambda v: validate_list_min_len(v, 1),  # pyright: ignore[reportArgumentType]
                    lambda v: validate_list_all_unique(v, keys=["name"]),  # pyright: ignore[reportArgumentType]
                ],
                value=val,
            ),
        }
    )

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
