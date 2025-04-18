from __future__ import annotations

import contextlib
import hashlib
import re
import sys
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from functools import cached_property

from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.errors import ValidationError
from variantlib.models.base import BaseModel
from variantlib.validators import validate_and
from variantlib.validators import validate_list_all_unique
from variantlib.validators import validate_list_min_len
from variantlib.validators import validate_matches_re
from variantlib.validators import validate_type

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@dataclass(frozen=True, order=True)
class VariantFeature(BaseModel):
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
    feature: str = field(
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

    @cached_property
    def feature_hash(self) -> int:
        # __class__ is being added to guarantee the hash to be specific to this class
        # note: can't use `self.__class__` because of inheritance
        return hash((VariantFeature, self.namespace, self.feature))

    def to_str(self) -> str:
        # Variant: <namespace> :: <feature> :: <val>
        return f"{self.namespace} :: {self.feature}"

    def serialize(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def deserialize(cls, data: dict[str, str]) -> Self:
        for field_name in cls.__dataclass_fields__:
            if field_name not in data:
                raise ValidationError(f"Extra field not known: `{field_name}`")
        return cls(**data)

    @classmethod
    def from_str(cls, input_str: str) -> Self:
        # removing starting `^` and trailing `$`
        pttn_nmspc = VALIDATION_NAMESPACE_REGEX[1:-1]
        pttn_feature = VALIDATION_FEATURE_REGEX[1:-1]

        pattern = rf"^(?P<namespace>{pttn_nmspc})\s*::\s*(?P<feature>{pttn_feature})$"

        # Try matching the input string with the regex pattern
        match = re.match(pattern, input_str.strip())

        if match is None:
            raise ValidationError(
                f"Invalid format: `{input_str}`, expected format: "
                "'<namespace> :: <feature>'"
            )

        # Extract the namespace, feature, and value from the match groups
        namespace = match.group("namespace")
        feature = match.group("feature")

        # Return an instance of VariantFeature using the parsed values
        return cls(namespace=namespace, feature=feature)


@dataclass(frozen=True, order=True)
class VariantProperty(VariantFeature):
    value: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, str),
                    lambda v: validate_matches_re(v, VALIDATION_VALUE_REGEX),
                ],
                value=val,
            )
        }
    )

    @cached_property
    def property_hash(self) -> int:
        # __class__ is being added to guarantee the hash to be specific to this class
        return hash((self.__class__, self.namespace, self.feature, self.value))

    @cached_property
    def feature_object(self) -> VariantFeature:
        return VariantFeature(namespace=self.namespace, feature=self.feature)

    def to_str(self) -> str:
        # Variant: <namespace> :: <feature> :: <val>
        return f"{self.namespace} :: {self.feature} :: {self.value}"

    @classmethod
    def from_str(cls, input_str: str) -> Self:
        # removing starting `^` and trailing `$`
        pttn_nmspc = VALIDATION_NAMESPACE_REGEX[1:-1]
        pttn_feature = VALIDATION_FEATURE_REGEX[1:-1]
        pttn_value = VALIDATION_VALUE_REGEX[1:-1]

        pattern = rf"^(?P<namespace>{pttn_nmspc})\s*::\s*(?P<feature>{pttn_feature})\s*::\s*(?P<value>{pttn_value})$"  # noqa: E501

        # Try matching the input string with the regex pattern
        match = re.match(pattern, input_str.strip())

        if match is None:
            raise ValidationError(
                f"Invalid format: `{input_str}`, "
                "expected format: `<namespace> :: <feature> :: <value>`"
            )

        # Extract the namespace, feature, and value from the match groups
        namespace = match.group("namespace")
        feature = match.group("feature")
        value = match.group("value")

        # Return an instance of VariantProperty using the parsed values
        return cls(namespace=namespace, feature=feature, value=value)


@dataclass(frozen=True)
class VariantDescription(BaseModel):
    """
    A `Variant` is being described by a N >= 1 `VariantProperty`.
    Each informing the packaging toolkit about a unique `namespace-feature-value`
    combination.

    All together they identify the package producing a "variant hash", unique
    to the exact combination of `VariantProperty` provided for a given package.
    """

    properties: list[VariantProperty] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[VariantProperty]),
                    lambda v: validate_list_min_len(v, 1),
                    lambda v: validate_list_all_unique(
                        v, keys=["namespace", "feature"]
                    ),
                ],
                value=val,
            ),
        }
    )

    def __post_init__(self) -> None:
        # We sort the data so that they always get displayed/hashed
        # in a consistent manner.
        # Note: We have to execute this before validation to guarantee hash consistency.

        with contextlib.suppress(AttributeError):
            # Only "legal way" to modify a frozen dataclass attribute post init.
            object.__setattr__(self, "properties", sorted(self.properties))

        # Execute the validator
        super().__post_init__()

    @cached_property
    def hexdigest(self) -> str:
        """
        Compute the hash of the object.
        """
        hash_object = hashlib.shake_128()
        for vprop in self.properties:
            hash_object.update(vprop.to_str().encode("utf-8"))

        # Like digest() except the digest is returned as a string object of double
        # length, containing only hexadecimal digits. This may be used to exchange the
        # value safely in email or other non-binary environments.
        # Source: https://docs.python.org/3/library/hashlib.html#hashlib.hash.hexdigest
        return hash_object.hexdigest(int(VARIANT_HASH_LEN / 2))

    @classmethod
    def deserialize(cls, properties: list[dict[str, str]]) -> Self:
        return cls(
            properties=[VariantProperty.deserialize(vdata) for vdata in properties]
        )

    def serialize(self) -> list[dict[str, str]]:
        return [vprop.serialize() for vprop in self.properties]

    def pretty_print(self) -> str:
        result_str = f"{'#' * 30} Variant: `{self.hexdigest}` {'#' * 29}"
        for vprop in self.properties:
            result_str += f"\nVariant Property: {vprop.to_str()}"
        result_str += f"\n{'#' * 80}\n"
        return result_str


@dataclass(frozen=True)
class VariantValidationResult:
    results: dict[VariantProperty, bool | None]

    def is_valid(self, allow_unknown_plugins: bool = True) -> bool:
        return False not in self.results.values() and (
            allow_unknown_plugins or None not in self.results.values()
        )

    @cached_property
    def invalid_properties(self) -> list[VariantProperty]:
        """List of properties declared invalid by plugins"""
        return [x for x, y in self.results.items() if y is False]

    @cached_property
    def unknown_properties(self) -> list[VariantProperty]:
        """List of properties not in any recognized namespace"""
        return [x for x, y in self.results.items() if y is None]
