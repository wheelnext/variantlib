import contextlib
import hashlib
import re
from collections.abc import Iterator
from typing import Self

from attrs import Converter
from attrs import field
from attrs import frozen
from attrs import validators

from variantlib.constants import VALIDATION_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANT_HASH_LEN


@frozen
class VariantMeta:
    provider: str = field(
        validator=[
            validators.instance_of(str),
            validators.matches_re(VALIDATION_REGEX),
        ]
    )
    key: str = field(
        validator=[
            validators.instance_of(str),
            validators.matches_re(VALIDATION_REGEX),
        ]
    )
    value: str = field(
        validator=[
            validators.instance_of(str),
            validators.matches_re(VALIDATION_VALUE_REGEX),
        ]
    )

    def __hash__(self) -> int:
        # Variant Metas are unique in provider & key and ignore the value.
        return hash((self.__class__, self.provider, self.key))

    def to_str(self) -> str:
        # Variant: <provider> :: <key> :: <val>
        return f"{self.provider} :: {self.key} :: {self.value}"

    @classmethod
    def from_str(cls, input_str: str) -> Self:
        subpattern = VALIDATION_REGEX[1:-1]  # removing starting `^` and trailing `$`
        pattern = rf"^(?P<provider>{subpattern}) :: (?P<key>{subpattern}) :: (?P<value>{subpattern})$"  # noqa: E501

        # Try matching the input string with the regex pattern
        match = re.match(pattern, input_str.strip())

        if match is None:
            raise ValueError(
                f"Invalid format: {input_str}. "
                "Expected format: '<provider> :: <key> :: <value>'"
            )

        # Extract the provider, key, and value from the match groups
        provider = match.group("provider")
        key = match.group("key")
        value = match.group("value")

        # Return an instance of VariantMeta using the parsed values
        return cls(provider=provider, key=key, value=value)


def _sort_variantmetas(value: list[VariantMeta]) -> list[VariantMeta]:
    # We sort the data so that they always get displayed/hashed
    # in a consistent manner.
    with contextlib.suppress(AttributeError):
        return sorted(value, key=lambda x: (x.provider, x.key))
    # Error will be rejected during validation
    return value


@frozen
class VariantDescription:
    """
    A `Variant` is being described by a N >= 1 `VariantMeta` metadata.
    Each informing the packaging toolkit about a unique `provider-key-value`
    combination.

    All together they identify the package producing a "variant hash", unique
    to the exact combination of `VariantMeta` provided for a given package.
    """

    data: list[VariantMeta] = field(
        validator=validators.instance_of(list), converter=Converter(_sort_variantmetas)
    )

    @data.validator
    def validate_data(self, _, data: list[VariantMeta]) -> None:
        """The field `data` must comply with the following
        - Being a non-empty list of `VariantMeta`
        - Each value inside the list must be unique
        """
        assert len(data) > 0
        assert all(isinstance(inst, VariantMeta) for inst in data)

        # Detect multiple `VariantMeta` with identical provider/key
        # Ignores the attribute `value` of `VariantMeta`.
        # Uses `__hash__` for collision detection.
        #
        # Note: Can not use `data = set(data)` in order to raise
        #       an exception when there is a collision instead of
        #       a silent behavior.
        seen = set()
        for vmeta in data:
            vmeta_hash = hash(vmeta)
            if vmeta_hash in seen:
                raise ValueError(
                    "Duplicate value for:\n"
                    f"\t- `provider`: {vmeta.provider}\n"
                    f"\t- `key`: {vmeta.key}"
                )
            seen.add(vmeta_hash)

    def __iter__(self) -> Iterator[VariantMeta]:
        yield from self.data

    @property
    def hexdigest(self) -> str:
        hash_object = hashlib.shake_128()
        for vmeta in self:
            hash_object.update(vmeta.to_str().encode("utf-8"))

        return hash_object.hexdigest(int(VARIANT_HASH_LEN / 2))
