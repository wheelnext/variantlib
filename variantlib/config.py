import re

from attrs import field
from attrs import frozen
from attrs import validators

from variantlib.constants import VALIDATION_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX


@frozen
class KeyConfig:
    key: str = field(
        validator=[
            validators.instance_of(str),
            validators.matches_re(VALIDATION_REGEX),
        ]
    )

    # Acceptable values in priority order
    values: list[str] = field(validator=validators.instance_of(list))

    @values.validator
    def validate_configs(self, _, data: list[str]) -> None:
        """The field `values` must comply with the following
        - Being a non-empty list of string
        - Each value inside the list must be unique
        - Each value inside the list must comply with `VALIDATION_VALUE_REGEX`
        """
        assert len(data) > 0
        assert all(isinstance(config, str) for config in data)

        seen = set()
        for value in data:
            if value in seen:
                raise ValueError(f"Duplicate value found: '{value}' in `values`.")

            if re.match(VALIDATION_VALUE_REGEX, value) is None:
                raise ValueError(
                    f"The value '{value}' does not follow the proper format."
                )

            seen.add(value)


@frozen
class ProviderConfig:
    provider: str = field(
        validator=[
            validators.instance_of(str),
            validators.matches_re(VALIDATION_REGEX),
        ]
    )

    # `KeyConfigs` in priority order
    configs: list[KeyConfig] = field(validator=validators.instance_of(list))

    @configs.validator
    def validate_configs(self, _, data: list[KeyConfig]) -> None:
        """The field `configs` must comply with the following
        - Being a non-empty list of `KeyConfig`
        - Each value inside the list must be unique
        """
        assert len(data) > 0
        assert all(isinstance(config, KeyConfig) for config in data)

        # Check that no KeyConfig has duplicate keys
        seen = set()
        for config in data:
            key = config.key
            if key in seen:
                raise ValueError(f"Duplicate `KeyConfig` for {key=} found.")
            seen.add(key)

    def pretty_print(self) -> str:
        result_str = f"{'#' * 20} Provider Config: `{self.provider}` {'#' * 20}"
        for kid, vconfig in enumerate(self.configs):
            result_str += (
                f"\n\t- Variant Config [{kid + 1:03d}]: "
                f"{vconfig.key} :: {vconfig.values}"  # noqa: PD011
            )
        result_str += f"\n{'#' * 80}\n"
        return result_str
