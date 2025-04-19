from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.filtering import filter_variants_by_features
from variantlib.resolver.filtering import filter_variants_by_namespaces
from variantlib.resolver.filtering import filter_variants_by_property
from variantlib.resolver.filtering import remove_duplicates
from variantlib.resolver.sorting import sort_variant_properties
from variantlib.resolver.sorting import sort_variants_descriptions
from variantlib.validators import validate_type

if TYPE_CHECKING:
    from collections.abc import Generator


def filter_variants(
    vdescs: list[VariantDescription],
    allowed_properties: list[VariantProperty],
    forbidden_namespaces: list[str] | None = None,
    forbidden_features: list[VariantFeature] | None = None,
    forbidden_properties: list[VariantProperty] | None = None,
) -> Generator[VariantDescription]:
    """
    Filters out a `list` of `VariantDescription` with the following filters:
    - Duplicates removed
    - Only allowed `variant properties` kept

    # Optionally:
    - Forbidden `variant namespaces` removed - if `forbidden_namespaces` is not None
    - Forbidden `variant features` removed - if `forbidden_features` is not None
    - Forbidden `variant properties` removed - if `forbidden_properties` is not None

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_properties: List of allowed `VariantProperty`.
    :param forbidden_namespaces: List of forbidden variant namespaces as `str`.
    :param forbidden_features: List of forbidden `VariantFeature`.
    :param forbidden_properties: List of forbidden `VariantProperty`.
    :return: Filtered list of `VariantDescription`.
    """

    # Input validation
    validate_type(vdescs, list[VariantDescription])
    validate_type(allowed_properties, list[VariantProperty])

    if forbidden_namespaces is not None:
        validate_type(forbidden_namespaces, list[str])

    if forbidden_features is not None:
        validate_type(forbidden_features, list[VariantFeature])

    if forbidden_properties is not None:
        validate_type(forbidden_properties, list[VariantProperty])

    # Step 1
    # Remove duplicates - There should never be any duplicates on the index
    #     - filename collision (same filename & same hash)
    #     - hash collision inside `variants.json`
    #     => Added for safety and to avoid any potential bugs
    #     (Note: In all fairness, even if it was to happen, it would most
    #            likely not be a problem given that we just pick the best match)
    result = remove_duplicates(vdescs)

    # Step 2 [Optional]
    # Remove any `VariantDescription` which declares any `VariantProperty` with
    # a variant namespace explicitly forbidden by the user.
    if forbidden_namespaces is not None:
        result = filter_variants_by_namespaces(
            vdescs=result,
            forbidden_namespaces=forbidden_namespaces,
        )

    # Step 3 [Optional]
    # Remove any `VariantDescription` which declares any `VariantProperty` with
    # `namespace :: feature` (aka. `VariantFeature`) explicitly forbidden by the user.
    if forbidden_features is not None:
        result = filter_variants_by_features(
            vdescs=result,
            forbidden_features=forbidden_features,
        )

    # Step 4 [Optional]
    # Remove any `VariantDescription` which declare any `VariantProperty`
    # `namespace :: feature :: value` unsupported on this platform or  explicitly
    #  forbidden by the user.
    if allowed_properties is not None:
        result = filter_variants_by_property(
            vdescs=result,
            allowed_properties=allowed_properties,
            forbidden_properties=forbidden_properties,
        )

    yield from result


def sort_and_filter_supported_variants(
    vdescs: list[VariantDescription],
    supported_vprops: list[VariantProperty],
    forbidden_namespaces: list[str] | None = None,
    forbidden_features: list[VariantFeature] | None = None,
    forbidden_properties: list[VariantProperty] | None = None,
    namespace_priorities: list[str] | None = None,
    feature_priorities: list[VariantFeature] | None = None,
    property_priorities: list[VariantProperty] | None = None,
) -> list[VariantDescription]:
    """
    Sort and filter a list of `VariantDescription` objects based on their
    `VariantProperty`s.

    :param vdescs: List of `VariantDescription` objects.
    :param supported_vprops: List of `VariantProperty` objects supported on the platform
    :param namespace_priorities: Ordered list of `str` objects.
    :param feature_priorities: Ordered list of `VariantFeature` objects.
    :param property_priorities: Ordered list of `VariantProperty` objects.
    :return: Sorted and filtered list of `VariantDescription` objects.
    """
    validate_type(vdescs, list[VariantDescription])

    if supported_vprops is None:
        """No supported properties provided, return no variants."""
        return []

    validate_type(supported_vprops, list[VariantProperty])

    # Step 1: we remove any duplicate, or unsupported `VariantDescription` on
    #         this platform.
    filtered_vdescs = list(
        filter_variants(
            vdescs=vdescs,
            allowed_properties=supported_vprops,
            forbidden_namespaces=forbidden_namespaces,
            forbidden_features=forbidden_features,
            forbidden_properties=forbidden_properties,
        )
    )

    # Step 2: we sort the supported `VariantProperty`s based on their respective
    #         priority.
    sorted_supported_vprops = sort_variant_properties(
        vprops=supported_vprops,
        property_priorities=property_priorities,
        feature_priorities=feature_priorities,
        namespace_priorities=namespace_priorities,
    )

    # Step 3: we sort the `VariantDescription` based on the sorted supported properties
    #         and their respective priority.
    return sort_variants_descriptions(
        filtered_vdescs,
        property_priorities=sorted_supported_vprops,
    )
