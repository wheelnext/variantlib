from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.models.validators import validate_instance_of
from variantlib.models.validators import validate_list_of
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.resolver.filtering import filter_variants_by_features
from variantlib.resolver.filtering import filter_variants_by_namespaces
from variantlib.resolver.filtering import filter_variants_by_property
from variantlib.resolver.filtering import remove_duplicates
from variantlib.resolver.sorting import sort_variant_properties
from variantlib.resolver.sorting import sort_variants_descriptions

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.models.variant import VariantFeature


def filter_variants(
    vdescs: list[VariantDescription],
    allowed_namespaces: list[str] | None = None,
    allowed_features: list[VariantFeature] | None = None,
    allowed_properties: list[VariantProperty] | None = None,
) -> Generator[VariantDescription]:
    """
    Filters out a `list` of `VariantDescription` with the following filters:
    - Duplicates removed
    - Unsupported `variant namespaces` removed - if `allowed_namespaces` is not None
    - Unsupported `variant features` removed - if `allowed_features` is not None
    - Unsupported `variant feature values` removed - if `allowed_properties` is not None

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_namespaces: List of allowed variant namespaces as `str`.
    :param allowed_features: List of allowed `VariantFeature`.
    :param allowed_properties: List of allowed `VariantProperty`.
    :return: Filtered list of `VariantDescription`.
    """

    # ========================= IMPLEMENTATION NOTE ========================= #
    # Technically, only step 4 is absolutely necessary to filter out the
    # `VariantDescription` that are not supported on this platform.
    # 1. There should never be any duplicates on the index
    #     - filename collision (same filename & same hash)
    #     - hash collision inside `variants.json`
    #     => Added for safety and to avoid any potential bugs
    #     (Note: In all fairness, even if it was to happen, it would most
    #            likely not be a problem given that we just pick the best match
    # 2. namespaces are included inside the `VariantProperty` of step 4
    # 3. features are included inside the `VariantProperty` of step 4
    #
    # However, I (Jonathan Dekhtiar) strongly recommend to keep all of them:
    # - Easier to read and understand
    # - Easier to debug
    # - Easier to maintain
    # - Easier to extend
    # - Easier to test
    # - Allows `tooling` to provide CLI/configuration flags to explicitly
    #   reject a `namespace` or `namespace::feature` without complex
    #   processing.
    # ======================================================================= #

    # Step 1: Remove duplicates - should never happen, but just in case
    result = remove_duplicates(vdescs)

    # Step 2: Remove any `VariantDescription` which declare any `VariantProperty` with
    # a variant namespace unsupported on this platform.
    if allowed_namespaces is not None:
        result = filter_variants_by_namespaces(
            vdescs=result,
            allowed_namespaces=allowed_namespaces,
        )

    # Step 3: Remove any `VariantDescription` which declare any `VariantProperty` with
    # `namespace :: feature` (aka. `VariantFeature`) unsupported on this platform.
    if allowed_features is not None:
        result = filter_variants_by_features(
            vdescs=result, allowed_features=allowed_features
        )

    # Step 4: Remove any `VariantDescription` which declare any `VariantProperty`
    # `namespace :: feature :: value` unsupported on this platform.
    if allowed_properties is not None:
        result = filter_variants_by_property(
            vdescs=result, allowed_properties=allowed_properties
        )

    yield from result


def sort_and_filter_supported_variants(
    vdescs: list[VariantDescription],
    supported_vprops: list[VariantProperty] | None = None,
    property_priorities: list[VariantProperty] | None = None,
    feature_priorities: list[VariantFeature] | None = None,
    namespace_priorities: list[str] | None = None,
) -> list[VariantDescription]:
    """
    Sort and filter a list of `VariantDescription` objects based on their
    `VariantProperty`s.

    :param vdescs: List of `VariantDescription` objects.
    :param supported_vprops: List of `VariantProperty` objects supported on the platform
    :param property_priorities: Ordered list of `VariantProperty` objects.
    :param feature_priorities: Ordered list of `VariantFeature` objects.
    :param namespace_priorities: Ordered list of `str` objects.
    :return: Sorted and filtered list of `VariantDescription` objects.
    """
    validate_instance_of(vdescs, list)
    validate_list_of(vdescs, VariantDescription)

    if supported_vprops is None:
        """No sdupported properties provided, return no variants."""
        return []

    validate_instance_of(supported_vprops, list)
    validate_list_of(supported_vprops, VariantProperty)

    # Step 1: we remove any duplicate, or unsupported `VariantDescription` on
    #         this platform.
    filtered_vdescs = list(
        filter_variants(
            vdescs=vdescs,
            allowed_namespaces=namespace_priorities,
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
