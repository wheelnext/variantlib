from __future__ import annotations

import logging
import sys
from itertools import chain
from itertools import groupby

from variantlib.errors import ConfigurationError
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.protocols import VariantFeatureName
from variantlib.protocols import VariantFeatureValue
from variantlib.protocols import VariantNamespace
from variantlib.validators.base import validate_type

logger = logging.getLogger(__name__)


def get_property_priorities(
    vprop: VariantProperty,
    property_priorities: dict[
        VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
    ]
    | None,
) -> int:
    """
    Get the property priority of a `VariantProperty` object.

    :param vprop: `VariantProperty` object.
    :param property_priorities: property priority dict
    :return: Property priority of the `VariantProperty` object.
    """
    validate_type(vprop, VariantProperty)

    if property_priorities is None:
        return sys.maxsize
    validate_type(
        property_priorities,
        dict[VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]],
    )

    # if not present push at the end
    try:
        return (
            property_priorities.get(vprop.namespace, {})
            .get(vprop.feature, [])
            .index(vprop.value)
        )
    except ValueError:
        return sys.maxsize


def get_feature_priorities(
    vprop: VariantProperty,
    feature_priorities: dict[VariantNamespace, list[VariantFeatureName]] | None,
) -> int:
    """
    Get the feature priority of a `VariantProperty` object.

    :param vprop: `VariantProperty` object.
    :param feature_priorities: feature priority dict
    :return: Feature priority of the `VariantProperty` object.
    """
    validate_type(vprop, VariantProperty)

    if feature_priorities is None:
        return sys.maxsize
    validate_type(feature_priorities, dict[VariantNamespace, list[VariantFeatureName]])

    # if not present push at the end
    try:
        return feature_priorities.get(vprop.namespace, []).index(vprop.feature)
    except ValueError:
        return sys.maxsize


def get_namespace_priorities(
    vprop: VariantProperty,
    namespace_priorities: list[VariantNamespace] | None,
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


def sort_variant_properties(
    vprops: list[VariantProperty],
    namespace_priorities: list[VariantNamespace] | None,
    feature_priorities: dict[VariantNamespace, list[VariantFeatureName]] | None = None,
    property_priorities: dict[
        VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
    ]
    | None = None,
) -> list[VariantProperty]:
    """
    Sort a list of `VariantProperty` objects based on their priority.

    :param vprops: List of `VariantProperty` objects.
    :param namespace_priorities: namespace priority list
    :param feature_priorities: feature priority dict
    :param property_priorities: property priority dict
    :return: Sorted list of `VariantProperty` objects.
    """
    validate_type(vprops, list[VariantProperty])

    if namespace_priorities is not None:
        validate_type(namespace_priorities, list[VariantNamespace])
    if feature_priorities is not None:
        validate_type(
            feature_priorities, dict[VariantNamespace, list[VariantFeatureName]]
        )
    if property_priorities is not None:
        validate_type(
            property_priorities,
            dict[VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]],
        )

    error_message = (
        "The variant environment needs to be (re)configured, please execute "
        "`variantlib config setup` and re-run your command."
    )

    found_namespaces = {vprop.namespace for vprop in vprops}

    if namespace_priorities is None or not namespace_priorities:
        if len(found_namespaces) > 1:
            raise ConfigurationError(error_message)

        # if there is only one namespace, use it as the default
        namespace_priorities = list(found_namespaces)

    elif len(found_namespaces.difference(namespace_priorities)) > 0:
        raise ConfigurationError(error_message)

    # 1. Reorder properties according to namespace priorities.
    sorted_by_namespace = sorted(
        vprops, key=lambda x: get_namespace_priorities(x, namespace_priorities)
    )

    # 2. Reorder properties within a namespace according to feature priorities.
    sorted_by_feature = chain.from_iterable(
        [
            sorted(
                namespace_properties,
                key=lambda x: get_feature_priorities(x, feature_priorities),
            )
            for _, namespace_properties in groupby(
                sorted_by_namespace, key=lambda x: x.namespace
            )
        ]
    )

    # 3. Reorder properties within a feature according to property priorities.
    sorted_by_property = chain.from_iterable(
        [
            sorted(
                feature_properties,
                key=lambda x: get_property_priorities(x, property_priorities),
            )
            for _, feature_properties in groupby(
                sorted_by_feature, key=lambda x: (x.namespace, x.feature)
            )
        ]
    )

    return list(sorted_by_property)


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

        if vdesc.is_null_variant():
            # return the tuple that represents the lowest priority
            return tuple(sys.maxsize for _ in property_hash_priorities)

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
