from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from variantlib.models.validators import validate_type
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
    validate_type(vdescs, Iterable)

    seen = set()

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the namespaces in the variant description are not allowed.
        """
        validate_type(vdesc, VariantDescription)

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
    vdescs: Iterable[VariantDescription],
    allowed_namespaces: list[str],
    forbidden_namespaces: list[str] | None = None,
) -> Generator[VariantDescription]:
    """
    Filters out `VariantDescription` that contain any unsupported variant namespace.

    ** Implementation Note:**
    - Installer will provide the list of allowed namespaces from variant provider
      plugins.
    - User can [optionally] provide a list of forbidden namespaces to be excluded.
      Forbidden namespaces take precedence of "allowed namespaces" and will be excluded.

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_namespaces: List of allowed variant namespaces as `str`.
                               Any variant namespace not explicitly allowed is forbidden
    :param forbidden_namespaces: List of forbidden variant namespaces as `str`.
    :return: Filtered list of `VariantDescription`.
    """

    if forbidden_namespaces is None:
        forbidden_namespaces = []

    # Input validation
    validate_type(vdescs, Iterable)
    validate_type(allowed_namespaces, list[str])
    validate_type(forbidden_namespaces, list[str])

    # Note: for performance reasons we convert the list to a set to avoid O(n) lookups
    _allowed_namespaces = set(allowed_namespaces)

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the namespaces in the variant description are not allowed.
        """
        validate_type(vdesc, VariantDescription)

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
    vdescs: Iterable[VariantDescription],
    allowed_features: list[VariantFeature],
    forbidden_features: list[VariantFeature] | None = None,
) -> Generator[VariantDescription]:
    """
    Filters out `VariantDescription` that contain any unsupported variant feature.

    ** Implementation Note:**
    - Installer will provide the list of allowed features from variant provider plugins.
    - User can [optionally] provide a list of forbidden features to be excluded.
      Forbidden features take precedence of "allowed features" and will be excluded.

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_features: List of allowed `VariantFeature`.
    :param forbidden_features: List of forbidden `VariantFeature`.
    :return: Filtered list of `VariantDescription`.
    """

    if forbidden_features is None:
        forbidden_features = []

    # Input validation
    validate_type(vdescs, Iterable)
    validate_type(allowed_features, list[VariantFeature])
    validate_type(forbidden_features, list[VariantFeature])

    # for performance reasons we convert the list to a set to avoid O(n) lookups
    allowed_feature_hexs = {vfeat.feature_hash for vfeat in allowed_features}
    forbidden_feature_hexs = {vfeat.feature_hash for vfeat in forbidden_features}

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the VariantFeatures in the variant description are not allowed.
        """
        validate_type(vdesc, VariantDescription)

        if forbidden_vprops := [
            vprop
            for vprop in vdesc.properties
            if (
                vprop.feature_hash not in allowed_feature_hexs
                or vprop.feature_hash in forbidden_feature_hexs
            )
        ]:
            logger.info(
                "Variant `%(vhash)s` has been rejected because one or many of the "
                "variant features `[%(vprops)s]` is not supported on this platform.",
                {
                    "vhash": vdesc.hexdigest,
                    "vprops": ", ".join([vprop.to_str() for vprop in forbidden_vprops]),
                },
            )
            return False

        return True

    yield from filter(_should_include, vdescs)


def filter_variants_by_property(
    vdescs: Iterable[VariantDescription],
    allowed_properties: list[VariantProperty],
    forbidden_properties: list[VariantProperty] | None = None,
) -> Generator[VariantDescription]:
    """
    Filters out `VariantDescription` that contain any unsupported variant property.

    ** Implementation Note:**
    - Installer will provide the list of allowed properties from variant provider
      plugins.
    - User can [optionally] provide a list of forbidden properties to be excluded.
      Forbidden properties take precedence of "allowed properties" and will be excluded.

    :param vdescs: list of `VariantDescription` to filter.
    :param allowed_properties: List of allowed `VariantProperty`.
    :param forbidden_properties: List of forbidden `VariantProperty`.
    :return: Filtered list of `VariantDescription`.
    """

    if forbidden_properties is None:
        forbidden_properties = []

    # Input validation
    validate_type(vdescs, Iterable)
    validate_type(allowed_properties, list[VariantProperty])
    validate_type(forbidden_properties, list[VariantProperty])

    # for performance reasons we convert the list to a set to avoid O(n) lookups
    allowed_properties_hexs = {vfeat.property_hash for vfeat in allowed_properties}
    forbidden_properties_hexs = {vfeat.property_hash for vfeat in forbidden_properties}

    def _should_include(vdesc: VariantDescription) -> bool:
        """
        Check if any of the namespaces in the variant description are not allowed.
        """
        validate_type(vdesc, VariantDescription)

        if forbidden_vprops := [
            vprop
            for vprop in vdesc.properties
            if (
                vprop.property_hash not in allowed_properties_hexs
                or vprop.property_hash in forbidden_properties_hexs
            )
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
