from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.models.base import BaseModel
from variantlib.models.validators import validate_and
from variantlib.models.validators import validate_list_all_unique
from variantlib.models.validators import validate_list_matches_re
from variantlib.models.validators import validate_list_min_len
from variantlib.models.validators import validate_matches_re
from variantlib.models.validators import validate_type


@dataclass(frozen=True)
class VariantFeatureConfig(BaseModel):
    name: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, str),
                    lambda v: validate_matches_re(v, VALIDATION_FEATURE_REGEX),
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

    def pretty_print(self) -> str:
        result_str = f"{'#' * 20} Provider Config: `{self.namespace}` {'#' * 20}"
        for kid, vconfig in enumerate(self.configs):
            result_str += (
                f"\n\t- Variant Config [{kid + 1:03d}]: "
                f"{vconfig.name} :: {vconfig.values}"
            )
        result_str += f"\n{'#' * 80}\n"
        return result_str
