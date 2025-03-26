import contextlib
import hashlib
import re
import sys
from collections.abc import Iterator
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from variantlib.constants import VALIDATION_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.validators import validate_instance_of
from variantlib.validators import validate_list_of
from variantlib.validators import validate_matches_re


@dataclass(frozen=True)
class VariantMeta:
    namespace: str = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, str),
                lambda v: validate_matches_re(v, VALIDATION_REGEX),
            ]
        }
    )
    key: str = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, str),
                lambda v: validate_matches_re(v, VALIDATION_REGEX),
            ]
        }
    )
    value: str = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, str),
                lambda v: validate_matches_re(v, VALIDATION_VALUE_REGEX),
            ]
        }
    )

    def __post_init__(self):
        # Execute the validators
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            for validator in field_def.metadata.get("validators", []):
                validator(value)

    def __hash__(self) -> int:
        # Variant Metas are unique in namespace & key and ignore the value.
        return hash((self.__class__, self.namespace, self.key))

    def to_str(self) -> str:
        # Variant: <namespace> :: <key> :: <val>
        return f"{self.namespace} :: {self.key} :: {self.value}"

    @classmethod
    def from_str(cls, input_str: str) -> Self:
        subpattern = VALIDATION_REGEX[1:-1]  # removing starting `^` and trailing `$`
        pattern = rf"^(?P<namespace>{subpattern})\s*::\s*(?P<key>{subpattern})\s*::\s*(?P<value>{subpattern})$"  # noqa: E501

        # Try matching the input string with the regex pattern
        match = re.match(pattern, input_str.strip())

        if match is None:
            raise ValueError(
                f"Invalid format: {input_str}. "
                "Expected format: '<namespace> :: <key> :: <value>'"
            )

        # Extract the namespace, key, and value from the match groups
        namespace = match.group("namespace")
        key = match.group("key")
        value = match.group("value")

        # Return an instance of VariantMeta using the parsed values
        return cls(namespace=namespace, key=key, value=value)

    def serialize(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def deserialize(cls, data: dict[str, str]) -> Self:
        assert all(key in data for key in ["namespace", "key", "value"])
        return cls(**data)


@dataclass(frozen=True)
class VariantDescription:
    """
    A `Variant` is being described by a N >= 1 `VariantMeta` metadata.
    Each informing the packaging toolkit about a unique `namespace-key-value`
    combination.

    All together they identify the package producing a "variant hash", unique
    to the exact combination of `VariantMeta` provided for a given package.
    """

    data: list[VariantMeta] = field(
        metadata={
            "validators": [
                lambda v: validate_instance_of(v, list),
                lambda v: validate_list_of(v, VariantMeta),
            ]
        }
    )

    def __post_init__(self):
        # Execute the validators
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            for validator in field_def.metadata.get("validators", []):
                validator(value)

        # We verify `data` is not empty
        assert len(self.data) > 0

        # We sort the data so that they always get displayed/hashed
        # in a consistent manner.
        with contextlib.suppress(AttributeError):
            # Only "legal way" to modify a frozen dataclass attribute post init.
            object.__setattr__(
                self, "data", sorted(self.data, key=lambda x: (x.namespace, x.key))
            )

        # Detect multiple `VariantMeta` with identical namespace/key
        # Ignores the attribute `value` of `VariantMeta`.
        # Uses `__hash__` for collision detection.
        #
        # Note: Can not use `data = set(data)` in order to raise
        #       an exception when there is a collision instead of
        #       a silent behavior.
        seen = set()
        for vmeta in self.data:
            vmeta_hash = hash(vmeta)
            if vmeta_hash in seen:
                raise ValueError(
                    "Duplicate value for:\n"
                    f"\t- `namespace`: {vmeta.namespace}\n"
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

    @classmethod
    def deserialize(cls, data: list[dict[str, str]]) -> Self:
        return cls(data=[VariantMeta.deserialize(vdata) for vdata in data])

    def serialize(self) -> list[dict[str, str]]:
        return [vmeta.serialize() for vmeta in self.data]

    def pretty_print(self) -> str:
        result_str = f"{'#' * 30} Variant: `{self.hexdigest}` {'#' * 29}"
        for vmeta in self:
            result_str += f"\nVariant Metadata: {vmeta.to_str()}"
        result_str += f"\n{'#' * 80}\n"
        return result_str
