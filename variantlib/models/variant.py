from __future__ import annotations

import contextlib
import hashlib
import re
import sys
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from operator import attrgetter

from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.errors import ValidationError
from variantlib.models.base import BaseModel
from variantlib.models.validators import validate_and
from variantlib.models.validators import validate_instance_of
from variantlib.models.validators import validate_list_all_unique
from variantlib.models.validators import validate_list_min_len
from variantlib.models.validators import validate_list_of
from variantlib.models.validators import validate_matches_re

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@dataclass(frozen=True)
class VariantFeature(BaseModel):
    namespace: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_instance_of(v, str),
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
                    lambda v: validate_instance_of(v, str),
                    lambda v: validate_matches_re(v, VALIDATION_FEATURE_REGEX),
                ],
                value=val,
            )
        }
    )

    @property
    def feature_hash(self) -> int:
        return hash((self.namespace, self.feature))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VariantFeature):
            return NotImplemented
        return self.namespace == other.namespace and self.feature == other.feature

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
                f"Invalid format: {input_str}. Expected format: "
                "'<namespace> :: <feature>'"
            )

        # Extract the namespace, feature, and value from the match groups
        namespace = match.group("namespace")
        feature = match.group("feature")

        # Return an instance of VariantFeature using the parsed values
        return cls(namespace=namespace, feature=feature)


@dataclass(frozen=True)
class VariantProperty(VariantFeature):
    value: str = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_instance_of(v, str),
                    lambda v: validate_matches_re(v, VALIDATION_VALUE_REGEX),
                ],
                value=val,
            )
        }
    )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VariantProperty):
            return NotImplemented

        return (
            self.namespace == other.namespace
            and self.feature == other.feature
            and self.value == other.value
        )

    @property
    def property_hash(self) -> int:
        return hash((self.namespace, self.feature, self.value))

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
                f"Invalid format: {input_str}. "
                "Expected format: '<namespace> :: <feature> :: <value>'"
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
                    lambda v: validate_instance_of(v, list),
                    lambda v: validate_list_of(v, VariantProperty),
                    lambda v: validate_list_min_len(v, 1),
                    lambda v: validate_list_all_unique(
                        v, key=attrgetter("feature_hash")
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
            object.__setattr__(
                self,
                "properties",
                sorted(self.properties, key=lambda x: (x.namespace, x.feature)),
            )

        # Execute the validator
        super().__post_init__()

    @property
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
