from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from variantlib.models.validators import validate_instance_of
from variantlib.models.validators import validate_list_of
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)


def remove_duplicates(
    vdescs: Iterable[VariantDescription],
) -> Generator[VariantDescription]:
    # Input validation
    validate_instance_of(vdescs, Iterable)

    seen = set()

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the namespaces in the variant description are not allowed.
        """
        validate_instance_of(vdesc, VariantDescription)

        if vdesc.hexdigest in seen:
            logger.info(
                "Variant `%(vhash)s` has been removed because it is a duplicate",
                {"vhash": vdesc.hexdigest},
            )
            return False

        seen.add(vdesc.hexdigest)
        return True

    yield from filter(_should_include, vdescs)


def filter_variants_by_namespaces(
    vdescs: Iterable[VariantDescription], allowed_namespaces: list[str]
) -> Generator[VariantDescription]:
    """
    Filters out `VariantDescription` that contain any unsupported variant namespace.

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_namespaces: List of allowed variant namespaces as `str`.
    :return: Filtered list of `VariantDescription`.
    """

    # Input validation
    validate_instance_of(vdescs, Iterable)
    validate_instance_of(allowed_namespaces, list)
    validate_list_of(allowed_namespaces, str)

    # Note: for performance reasons we convert the list to a set to avoid O(n) lookups
    _allowed_namespaces = set(allowed_namespaces)

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the namespaces in the variant description are not allowed.
        """
        validate_instance_of(vdesc, VariantDescription)

        if any(
            vprop.namespace not in _allowed_namespaces for vprop in vdesc.properties
        ):
            logger.info(
                "Variant `%(vhash)s` has been rejected because one of variant "
                "namespaces `[%(namespaces)s]` is not allowed. Allowed: "
                "`[%(allowed_namespaces)s]`.",
                {
                    "vhash": vdesc.hexdigest,
                    "namespaces": ", ".join(
                        [vprop.namespace for vprop in vdesc.properties]
                    ),
                    "allowed_namespaces": ", ".join(_allowed_namespaces),
                },
            )
            return False

        return True

    yield from filter(_should_include, vdescs)


def filter_variants_by_features(
    vdescs: Iterable[VariantDescription], allowed_features: list[VariantFeature]
) -> Generator[VariantDescription]:
    """
    Filters out `VariantDescription` that contain any unsupported variant feature.

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_features: List of allowed `VariantFeature`.
    :return: Filtered list of `VariantDescription`.
    """

    # Input validation
    validate_instance_of(vdescs, Iterable)
    validate_instance_of(allowed_features, list)
    validate_list_of(allowed_features, VariantFeature)

    # for performance reasons we convert the list to a set to avoid O(n) lookups
    allowed_feature_hexs = {vfeat.feature_hash for vfeat in allowed_features}

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the namespaces in the variant description are not allowed.
        """
        validate_instance_of(vdesc, VariantDescription)

        if forbidden_vprops := [
            vprop
            for vprop in vdesc.properties
            if vprop.feature_hash not in allowed_feature_hexs
        ]:
            logger.info(
                "Variant `%(vhash)s` has been rejected because one of the variant "
                "features `[%(vprops)s]` is not supported on this platform.",
                {
                    "vhash": vdesc.hexdigest,
                    "vprops": ", ".join([vprop.to_str() for vprop in forbidden_vprops]),
                },
            )
            return False

        return True

    yield from filter(_should_include, vdescs)


def filter_variants_by_property(
    vdescs: Iterable[VariantDescription], allowed_properties: list[VariantProperty]
) -> Generator[VariantDescription]:
    """
    Filters out `VariantDescription` that contain any unsupported variant feature.

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_properties: List of allowed `VariantProperty`.
    :return: Filtered list of `VariantDescription`.
    """

    # Input validation
    validate_instance_of(vdescs, Iterable)
    validate_instance_of(allowed_properties, list)
    validate_list_of(allowed_properties, VariantProperty)

    # for performance reasons we convert the list to a set to avoid O(n) lookups
    allowed_properties_hexs = {vfeat.property_hash for vfeat in allowed_properties}

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the namespaces in the variant description are not allowed.
        """
        validate_instance_of(vdesc, VariantDescription)

        if forbidden_vprops := [
            vprop
            for vprop in vdesc.properties
            if vprop.property_hash not in allowed_properties_hexs
        ]:
            logger.info(
                "Variant `%(vhash)s` has been rejected because one of the variant "
                "features `[%(vprops)s]` is not supported on this platform.",
                {
                    "vhash": vdesc.hexdigest,
                    "vprops": ", ".join([vprop.to_str() for vprop in forbidden_vprops]),
                },
            )
            return False

        return True

    yield from filter(_should_include, vdescs)
