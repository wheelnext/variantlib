from __future__ import annotations

import logging
import sys

from variantlib.errors import ValidationError
from variantlib.models.validators import validate_type
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty

logger = logging.getLogger(__name__)


def get_property_priority(
    vprop: VariantProperty,
    property_priorities: list[VariantProperty] | None,
) -> int:
    """
    Get the property priority of a `VariantProperty` object.

    :param vprop: `VariantProperty` object.
    :param property_priorities: ordered list of `VariantProperty` objects.
    :return: Property priority of the `VariantProperty` object.
    """
    validate_type(vprop, VariantProperty)

    if property_priorities is None:
        return sys.maxsize
    validate_type(property_priorities, list[VariantProperty])

    _property_priorities = [vprop.property_hash for vprop in property_priorities]

    # if not present push at the end
    try:
        return _property_priorities.index(vprop.property_hash)
    except ValueError:
        return sys.maxsize


def get_feature_priority(
    vprop: VariantProperty,
    feature_priorities: list[VariantFeature] | None,
) -> int:
    """
    Get the feature priority of a `VariantProperty` object.

    :param vprop: `VariantProperty` object.
    :param feature_priorities: ordered list of `VariantFeature` objects.
    :return: Feature priority of the `VariantProperty` object.
    """
    validate_type(vprop, VariantProperty)

    if feature_priorities is None:
        return sys.maxsize
    validate_type(feature_priorities, list[VariantFeature])

    _feature_priorities = [vfeat.feature_hash for vfeat in feature_priorities]

    # if not present push at the end
    try:
        return _feature_priorities.index(vprop.feature_hash)
    except ValueError:
        return sys.maxsize


def get_namespace_priority(
    vprop: VariantProperty,
    namespace_priorities: list[str] | None,
) -> int:
    """
    Get the namespace priority of a `VariantProperty` object.

    :param vprop: `VariantProperty` object.
    :param namespace_priorities: ordered list of `str` objects.
    :return: Namespace priority of the `VariantProperty` object.
    """
    validate_type(vprop, VariantProperty)

    if namespace_priorities is None:
        return sys.maxsize
    validate_type(namespace_priorities, list[str])

    # if not present push at the end
    try:
        return namespace_priorities.index(vprop.namespace)
    except ValueError:
        return sys.maxsize


def get_variant_property_priority_tuple(
    vprop: VariantProperty,
    property_priorities: list[VariantProperty] | None,
    feature_priorities: list[VariantFeature] | None,
    namespace_priorities: list[str] | None,
) -> tuple[int, int, int]:
    """
    Get the variant property priority of a `VariantProperty` object.

    :param vprop: `VariantProperty` object.
    :param property_priorities: ordered list of `VariantProperty` objects.
    :param feature_priorities: ordered list of `VariantFeature` objects.
    :param namespace_priorities: ordered list of `str` objects.
    :return: Variant property priority of the `VariantProperty` object.
    """
    validate_type(vprop, VariantProperty)

    ranking_tuple = (
        # First Priority
        get_property_priority(vprop, property_priorities),
        # Second Priority
        get_feature_priority(vprop, feature_priorities),
        # Third Priority
        get_namespace_priority(vprop, namespace_priorities),
    )

    if all(x == sys.maxsize for x in ranking_tuple):
        raise ValidationError(
            f"VariantProperty {vprop} has no priority - this should not happen."
        )

    return ranking_tuple


def sort_variant_properties(
    vprops: list[VariantProperty],
    property_priorities: list[VariantProperty] | None,
    feature_priorities: list[VariantFeature] | None,
    namespace_priorities: list[str] | None,
) -> list[VariantProperty]:
    """
    Sort a list of `VariantProperty` objects based on their priority.

    :param vprops: List of `VariantProperty` objects.
    :param property_priorities: ordered list of `VariantProperty` objects.
    :param feature_priorities: ordered list of `VariantFeature` objects.
    :param namespace_priorities: ordered list of `str` objects.
    :return: Sorted list of `VariantProperty` objects.
    """
    validate_type(vprops, list[VariantProperty])

    return sorted(
        vprops,
        key=lambda x: get_variant_property_priority_tuple(
            x, property_priorities, feature_priorities, namespace_priorities
        ),
    )


def sort_variants_descriptions(
    vdescs: list[VariantDescription], property_priorities: list[VariantProperty]
) -> list[VariantDescription]:
    """
    Sort a list of `VariantDescription` objects based on their `VariantProperty`s.

    :param vdescs: List of `VariantDescription` objects.
    :param property_priorities: ordered list of `VariantProperty` objects.
    :return: Sorted list of `VariantDescription` objects.
    """
    validate_type(vdescs, list[VariantDescription])
    validate_type(property_priorities, list[VariantProperty])

    # Pre-compute the property hash for the property priorities
    # This is used to speed up the sorting process.
    # The property_hash is used to compare the `VariantProperty` objects
    property_hash_priorities = [vprop.property_hash for vprop in property_priorities]

    def _get_rank_tuple(vdesc: VariantDescription) -> tuple[int, ...]:
        """
        Get the rank tuple of a `VariantDescription` object.

        :param vdesc: `VariantDescription` object.
        :return: Rank tuple[int, ...] of the `VariantDescription` object.
        """

        # --------------------------- Implementation Notes --------------------------- #
        # - `property_hash_priorities` is ordered. It's a list.
        # - `vdesc_prop_hashes` is unordered. It's a set.
        #
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Performance Notes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
        # * Only `property_hash_priorities` needs to be ordered. The set is used for
        # performance reasons.
        # * `vdesc.properties` hashes are pre-computed and saved to avoid recomputing
        #  them multiple times.
        # * `property_priorities` are also pre-hashed to avoid recomputing them
        # ---------------------------------------------------------------------------- #

        # using a set for performance reason: O(1) access time.
        vdesc_prop_hashes = {vprop.property_hash for vprop in vdesc.properties}

        # N-dimensional tuple with tuple[N] of 1 or sys.maxsize
        # 1 if the property is present in the `VariantDescription` object,
        # sys.maxsize if not present.
        # This is used to sort the `VariantDescription` objects based on their
        # `VariantProperty`s.
        ranking_tuple = tuple(
            1 if vprop_hash in vdesc_prop_hashes else sys.maxsize
            for vprop_hash in property_hash_priorities
        )

        if sum(1 for x in ranking_tuple if x != sys.maxsize) != len(vdesc.properties):
            raise ValidationError(
                f"VariantDescription {vdesc} contains properties not in the property "
                "priorities list - this should not happen. Filtering should be applied "
                "first."
            )

        return ranking_tuple

    return sorted(vdescs, key=_get_rank_tuple)
