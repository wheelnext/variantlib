from __future__ import annotations

import logging
import os
from importlib import metadata
from typing import TYPE_CHECKING

from packaging.utils import canonicalize_name

from variantlib.constants import VARIANT_ABI_DEPENDENCY_NAMESPACE
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.filtering import filter_variants_by_features
from variantlib.resolver.filtering import filter_variants_by_namespaces
from variantlib.resolver.filtering import filter_variants_by_property
from variantlib.resolver.filtering import remove_duplicates
from variantlib.resolver.sorting import sort_variant_properties
from variantlib.resolver.sorting import sort_variants_descriptions
from variantlib.validators.base import validate_type

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.protocols import VariantFeatureName
    from variantlib.protocols import VariantFeatureValue
    from variantlib.protocols import VariantNamespace

logger = logging.getLogger(__name__)


def _normalize_package_name(name: str) -> str:
    # VALIDATION_FEATURE_NAME_REGEX does not accepts "-"
    return canonicalize_name(name).replace("-", "_")


def _normalize_package_version(version: str) -> str:
    # VALIDATION_VALUE_REGEX does not accepts "+"
    return version.split("+", maxsplit=1)[0]


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
    namespace_priorities: list[VariantNamespace] | None = None,
    feature_priorities: dict[VariantNamespace, list[VariantFeatureName]] | None = None,
    property_priorities: dict[
        VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
    ]
    | None = None,
    forbidden_namespaces: list[VariantNamespace] | None = None,
    forbidden_features: list[VariantFeature] | None = None,
    forbidden_properties: list[VariantProperty] | None = None,
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
    validate_type(supported_vprops, list[VariantProperty])

    if namespace_priorities is None:
        namespace_priorities = []

    # ======================================================================= #
    #                         ABI DEPENDENCY INJECTION                        #
    # ======================================================================= #

    # 1. Manually fed from environment variable
    #    Note: come first for "implicit higher priority"
    #    Env Var Format: `VARIANT_ABI_DEPENDENCY=packageA==1.2.3,...,packageZ==7.8.9`
    if variant_abi_deps_env := os.environ.get("NV_VARIANT_PROVIDER_FORCE_SM_ARCH"):
        for pkg_spec in variant_abi_deps_env.split(","):
            try:
                pkg_name, pkg_version = pkg_spec.split("==", maxsplit=1)
            except ValueError:
                logger.exception(
                    "`NV_VARIANT_PROVIDER_FORCE_SM_ARCH` received an invalid value "
                    "`%(pkg_spec)s`. It will be ignored.\n"
                    "Expected format: `packageA==1.2.3,...,packageZ==7.8.9`.",
                    {"pkg_spec": pkg_spec},
                )
                continue

            supported_vprops.append(
                VariantProperty(
                    namespace=VARIANT_ABI_DEPENDENCY_NAMESPACE,
                    feature=_normalize_package_name(pkg_name),
                    value=_normalize_package_version(pkg_version),
                )
            )

    # 2. Automatically populate from the current python environment
    packages = [
        (dist.metadata["Name"], dist.version) for dist in metadata.distributions()
    ]
    for pkg_name, pkg_version in sorted(packages):
        supported_vprops.append(
            VariantProperty(
                namespace=VARIANT_ABI_DEPENDENCY_NAMESPACE,
                feature=_normalize_package_name(pkg_name),
                value=_normalize_package_version(pkg_version),
            )
        )

    # 3. Adding `VARIANT_ABI_DEPENDENCY_NAMESPACE` at the back of`namespace_priorities`
    namespace_priorities.append(VARIANT_ABI_DEPENDENCY_NAMESPACE)

    # ======================================================================= #
    #                               NULL VARIANT                              #
    # ======================================================================= #

    # Adding the `null-variant` to the list - always "compatible"
    if (null_variant := VariantDescription()) not in vdescs:
        """Add a null variant description to the list."""
        # This is needed to ensure that we always consider the null variant
        # to fall back on when no other variants are available.
        #
        # This can be used to provide a different default build when using
        # a variant-enabled installer.
        vdescs.append(null_variant)

    if supported_vprops is None:
        """No supported properties provided, return no variants."""
        return []

    # ======================================================================= #
    #                                FILTERING                                #
    # ======================================================================= #

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

    # ======================================================================= #
    #                                 SORTING                                 #
    # ======================================================================= #

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
