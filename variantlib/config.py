from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field

from variantlib.constants import VALIDATION_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.validators import validate_instance_of
from variantlib.validators import validate_list_of
from variantlib.validators import validate_matches_re


@dataclass(frozen=True)
class KeyConfig:
    key: str = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, str),
                lambda v: validate_matches_re(v, VALIDATION_REGEX),
            ]
        }
    )

    # Acceptable values in priority order
    values: list[str] = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, list),
                lambda v: validate_list_of(v, str),
            ]
        }
    )

    def __post_init__(self) -> None:
        # Execute the validators
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            for validator in field_def.metadata.get("validators", []):
                validator(value)

        # We verify `values` is not empty
        assert len(self.values) > 0

        """The field `values` must comply with the following
        - Each value inside the list must be unique
        - Each value inside the list must comply with `VALIDATION_VALUE_REGEX`
        """
        seen = set()
        for value in self.values:
            if value in seen:
                raise ValueError(f"Duplicate value found: '{value}' in `values`.")

            if re.match(VALIDATION_VALUE_REGEX, value) is None:
                raise ValueError(
                    f"The value '{value}' does not follow the proper format."
                )

            seen.add(value)


@dataclass(frozen=True)
class ProviderConfig:
    namespace: str = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, str),
                lambda v: validate_matches_re(v, VALIDATION_REGEX),
            ]
        }
    )

    # `KeyConfigs` in priority order
    configs: list[KeyConfig] = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, list),
                lambda v: validate_list_of(v, KeyConfig),
            ]
        }
    )

    def __post_init__(self) -> None:
        # Execute the validators
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            for validator in field_def.metadata.get("validators", []):
                validator(value)

        # We verify `values` is not empty
        assert len(self.configs) > 0

        """The field `configs` must comply with the following
        - Each value inside the list must be unique
        """

        # Check that no KeyConfig has duplicate keys
        seen = set()
        for config in self.configs:
            key = config.key
            if key in seen:
                raise ValueError(f"Duplicate `KeyConfig` for {key=} found.")
            seen.add(key)

    def pretty_print(self) -> str:
        result_str = f"{'#' * 20} Provider Config: `{self.namespace}` {'#' * 20}"
        for kid, vconfig in enumerate(self.configs):
            result_str += (
                f"\n\t- Variant Config [{kid + 1:03d}]: "
                f"{vconfig.key} :: {vconfig.values}"
            )
        result_str += f"\n{'#' * 80}\n"
        return result_str
