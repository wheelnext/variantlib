from __future__ import annotations

import contextlib
import hashlib
import sys
from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from functools import cached_property

from variantlib.constants import VALIDATION_FEATURE_NAME_REGEX
from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.errors import ValidationError
from variantlib.models.base import BaseModel
from variantlib.validators.base import validate_list_all_unique
from variantlib.validators.base import validate_matches_re
from variantlib.validators.base import validate_type
from variantlib.validators.combining import validate_and

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
                    lambda v: validate_matches_re(v, VALIDATION_FEATURE_NAME_REGEX),
                ],
                value=val,
            )
        }
    )

    @property
    def feature_hash(self) -> int:
        # __class__ is being added to guarantee the hash to be specific to this class
        # note: can't use `self.__class__` because of inheritance
        return hash((VariantFeature, self.namespace, self.feature))

    def to_str(self) -> str:
        # Variant-Property: <namespace> :: <feature> :: <val>
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
        # Try matching the input string with the regex pattern
        match = VALIDATION_FEATURE_REGEX.fullmatch(input_str.strip())
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

    @property
    def property_hash(self) -> int:
        # __class__ is being added to guarantee the hash to be specific to this class
        return hash((self.__class__, self.namespace, self.feature, self.value))

    @property
    def feature_object(self) -> VariantFeature:
        return VariantFeature(namespace=self.namespace, feature=self.feature)

    def to_str(self) -> str:
        # Variant-Property: <namespace> :: <feature> :: <val>
        return f"{self.namespace} :: {self.feature} :: {self.value}"

    @classmethod
    def from_str(cls, input_str: str) -> Self:
        # Try matching the input string with the regex pattern
        match = VALIDATION_PROPERTY_REGEX.fullmatch(input_str.strip())

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
                    lambda v: validate_list_all_unique(
                        v, keys=["namespace", "feature"]
                    ),
                ],
                value=val,
            ),
        },
        default_factory=list,
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

    def is_null_variant(self) -> bool:
        """
        Check if the variant is a null variant.
        A null variant is a variant with no properties.
        """
        return not self.properties

    @cached_property
    def hexdigest(self) -> str:
        """
        Compute the hash of the object.
        """
        if self.is_null_variant():
            # The `null-variant` is a special case where no properties are defined.
            return "0" * VARIANT_HASH_LEN

        hash_object = hashlib.sha256()
        # Append a newline to every serialized property to ensure that they
        # are separated from one another. Otherwise, two "adjacent" variants
        # such as:
        #     a :: b :: cx
        #     d :: e :: f
        # and:
        #     a :: b :: c
        #     xd :: e :: f
        # would serialize to the same hash.
        for vprop in self.properties:
            hash_object.update(f"{vprop.to_str()}\n".encode())

        # Like digest() except the digest is returned as a string object of double
        # length, containing only hexadecimal digits. This may be used to exchange the
        # value safely in email or other non-binary environments.
        # Source: https://docs.python.org/3/library/hashlib.html#hashlib.hash.hexdigest
        return hash_object.hexdigest()[:VARIANT_HASH_LEN]

    @classmethod
    def deserialize(cls, properties: list[dict[str, str]]) -> Self:
        return cls(
            properties=[VariantProperty.deserialize(vdata) for vdata in properties]
        )

    def serialize(self) -> list[dict[str, str]]:
        return [vprop.serialize() for vprop in self.properties]

    def to_dict(self) -> dict[str, dict[str, str]]:
        data = asdict(self)

        result: defaultdict[str, dict[str, str]] = defaultdict(dict)

        for vprop in data["properties"]:
            namespace = vprop["namespace"]
            feature = vprop["feature"]
            value = vprop["value"]
            result[namespace][feature] = value

        return dict(result)

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, str]]) -> Self:
        vprops = [
            VariantProperty(namespace=namespace, feature=key, value=value)
            for namespace, vdata in data.items()
            for key, value in vdata.items()
        ]

        return cls(vprops)


@dataclass(frozen=True)
class VariantValidationResult:
    results: dict[VariantProperty, bool | None]

    def is_valid(self, allow_unknown_plugins: bool = True) -> bool:
        return False not in self.results.values() and (
            allow_unknown_plugins or None not in self.results.values()
        )

    @property
    def invalid_properties(self) -> list[VariantProperty]:
        """List of properties declared invalid by plugins"""
        return [x for x, y in self.results.items() if y is False]

    @property
    def unknown_properties(self) -> list[VariantProperty]:
        """List of properties not in any recognized namespace"""
        return [x for x, y in self.results.items() if y is None]
