from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Self

from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.models.base import BaseModel
from variantlib.models.validators import validate_and
from variantlib.models.validators import validate_instance_of
from variantlib.models.validators import validate_list_matches_re
from variantlib.models.validators import validate_list_of
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty


@dataclass(frozen=True)
class Configuration(BaseModel):
    """
    Configuration class for variantlib.

    This class is used to define the configuration for the variantlib library.
    It includes fields for the namespace, feature, and value, along with validation
    checks for each field.

    Attributes:
        namespaces_by_priority (list): The namespace of the configuration.
        features_by_priority (list): The feature of the configuration.
    """

    namespaces_priority: list[str] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_instance_of(v, list),
                    lambda v: validate_list_of(v, str),
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
                    lambda v: validate_instance_of(v, list),
                    lambda v: validate_list_of(v, VariantFeature),
                ],
                value=val,
            )
        }
    )

    property_priority: list[VariantProperty] = field(
        metadata={
            "validator": lambda val: validate_and(
                [
                    lambda v: validate_instance_of(v, list),
                    lambda v: validate_list_of(v, VariantProperty),
                ],
                value=val,
            )
        }
    )

    @classmethod
    def default(cls) -> Self:
        """
        Create a default Configuration instance.

        Returns:
            Configuration: A new Configuration instance with default values.
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
            for feature in features_priority:
                validate_instance_of(feature, str)
                _features_priority.append(VariantFeature.from_str(feature))

        # Convert the `property_priority: list[str]` into `list[VariantProperty]`
        _property_priority: list[VariantProperty] = []
        if property_priority is not None:
            for vprop in property_priority:
                validate_instance_of(vprop, str)
                _property_priority.append(VariantProperty.from_str(feature))

        return cls(
            namespaces_priority=namespaces_priority or [],
            features_priority=_features_priority,
            property_priority=_property_priority,
        )
