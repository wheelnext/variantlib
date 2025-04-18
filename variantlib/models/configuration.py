from __future__ import annotations

import sys
from dataclasses import dataclass
from dataclasses import field

from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.models.base import BaseModel
from variantlib.models.validators import validate_and
from variantlib.models.validators import validate_list_matches_re
from variantlib.models.validators import validate_type
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty

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
        namespaces_priority (list): Sorted list of "variant namespaces" by priority.
        features_priority (list): Sorted list of `VariantFeature` by priority.
        property_priority (list): Sorted list of `VariantProperty` by priority.
    """

    namespaces_priority: list[str] = field(
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

    features_priority: list[VariantFeature] = field(
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

    property_priority: list[VariantProperty] = field(
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
            namespaces_priority=[],
            features_priority=[],
            property_priority=[],
        )

    @classmethod
    def from_toml_config(
        cls,
        namespaces_priority: list[str] | None = None,
        features_priority: list[str] | None = None,
        property_priority: list[str] | None = None,
    ) -> Self:
        """
        Create a Configuration instance from TOML-based configuration.

        Returns:
            Configuration: A new Configuration instance.
        """

        # Convert the `features_priority: list[str]` into `list[VariantFeature]`
        _features_priority: list[VariantFeature] = []
        if features_priority is not None:
            for vfeat in features_priority:
                validate_type(vfeat, str)
                _features_priority.append(VariantFeature.from_str(vfeat))

        # Convert the `property_priority: list[str]` into `list[VariantProperty]`
        _property_priority: list[VariantProperty] = []
        if property_priority is not None:
            for vprop in property_priority:
                validate_type(vprop, str)
                _property_priority.append(VariantProperty.from_str(vprop))

        return cls(
            namespaces_priority=namespaces_priority or [],
            features_priority=_features_priority,
            property_priority=_property_priority,
        )
