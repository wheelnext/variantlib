from __future__ import annotations

import sys
from dataclasses import dataclass
from dataclasses import field

from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.models.base import BaseModel
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.validators import validate_and
from variantlib.validators import validate_list_matches_re
from variantlib.validators import validate_type

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


@dataclass(frozen=True)
class VariantConfiguration(BaseModel):
    """
    Configuration class for variantlib.

    This class is used to define the configuration for the variantlib library.
    It includes fields for the namespace, feature, and value, along with validation
    checks for each field.

    # Sorting Note: First is best.

    Attributes:
        namespace_priorities (list): Sorted list of "variant namespaces" by priority.
        feature_priorities (list): Sorted list of `VariantFeature` by priority.
        property_priorities (list): Sorted list of `VariantProperty` by priority.
    """

    namespace_priorities: list[str] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[str]),
                    lambda v: validate_list_matches_re(v, VALIDATION_NAMESPACE_REGEX),
                ],
                value=val,
            )
        }
    )

    feature_priorities: list[VariantFeature] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[VariantFeature]),
                ],
                value=val,
            )
        },
        default_factory=list,
    )

    property_priorities: list[VariantProperty] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[VariantProperty]),
                ],
                value=val,
            )
        },
        default_factory=list,
    )

    @classmethod
    def default(cls) -> Self:
        """
        Create a default `VariantConfiguration` instance.

        Returns:
            VariantConfiguration: A new instance with default values.
        """

        # TODO: Verify the default values make sense

        return cls(
            namespace_priorities=[],
            feature_priorities=[],
            property_priorities=[],
        )

    @classmethod
    def from_toml_config(
        cls,
        namespace_priorities: list[str] | None = None,
        feature_priorities: list[str] | None = None,
        property_priorities: list[str] | None = None,
    ) -> Self:
        """
        Create a Configuration instance from TOML-based configuration.

        Returns:
            Configuration: A new Configuration instance.
        """

        # Convert the `feature_priorities: list[str]` into `list[VariantFeature]`
        _feature_priorities: list[VariantFeature] = []
        if feature_priorities is not None:
            for vfeat in feature_priorities:
                validate_type(vfeat, str)
                _feature_priorities.append(VariantFeature.from_str(vfeat))

        # Convert the `property_priorities: list[str]` into `list[VariantProperty]`
        _property_priorities: list[VariantProperty] = []
        if property_priorities is not None:
            for vprop in property_priorities:
                validate_type(vprop, str)
                _property_priorities.append(VariantProperty.from_str(vprop))

        return cls(
            namespace_priorities=namespace_priorities or [],
            feature_priorities=_feature_priorities,
            property_priorities=_property_priorities,
        )
