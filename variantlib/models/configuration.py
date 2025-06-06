from __future__ import annotations

import sys
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.models.base import BaseModel
from variantlib.protocols import VariantFeatureName
from variantlib.protocols import VariantFeatureValue
from variantlib.protocols import VariantNamespace
from variantlib.validators.base import validate_list_matches_re
from variantlib.validators.base import validate_type
from variantlib.validators.combining import validate_and

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from typing import Any


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

    namespace_priorities: list[VariantNamespace] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(v, list[VariantNamespace]),
                    lambda v: validate_list_matches_re(v, VALIDATION_NAMESPACE_REGEX),
                ],
                value=val,
            )
        }
    )

    feature_priorities: dict[VariantNamespace, list[VariantFeatureName]] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(
                        v, dict[VariantNamespace, list[VariantFeatureName]]
                    ),
                    lambda v: validate_list_matches_re(
                        v.keys(), VALIDATION_NAMESPACE_REGEX
                    ),
                    # TODO
                ],
                value=val,
            )
        },
        default_factory=dict,
    )

    property_priorities: dict[
        VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
    ] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_type(
                        v,
                        dict[
                            VariantNamespace,
                            dict[VariantFeatureName, list[VariantFeatureValue]],
                        ],
                    ),
                    lambda v: validate_list_matches_re(
                        v.keys(), VALIDATION_NAMESPACE_REGEX
                    ),
                    # TODO
                ],
                value=val,
            )
        },
        default_factory=dict,
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
            feature_priorities={},
            property_priorities={},
        )

    @classmethod
    def from_toml_config(
        cls,
        namespace_priorities: list[VariantNamespace] | None = None,
        feature_priorities: dict[VariantNamespace, list[VariantFeatureName]]
        | None = None,
        property_priorities: dict[
            VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
        ]
        | None = None,
    ) -> Self:
        """
        Create a Configuration instance from TOML-based configuration.

        Returns:
            Configuration: A new Configuration instance.
        """

        return cls(
            namespace_priorities=namespace_priorities or [],
            feature_priorities=feature_priorities or {},
            property_priorities=property_priorities or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the Configuration instance to a dictionary.

        Returns:
            dict: A dictionary representation of the Configuration instance.
        """
        return {
            "namespace_priorities": self.namespace_priorities,
            "feature_priorities": self.feature_priorities,
            "property_priorities": self.property_priorities,
        }
