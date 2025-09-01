"""This file regroups the public API of the variantlib package."""

from __future__ import annotations

import itertools
import logging
import pathlib
from typing import TYPE_CHECKING

from variantlib.configuration import VariantConfiguration
from variantlib.constants import NULL_VARIANT_LABEL
from variantlib.constants import VALIDATION_VARIANT_LABEL_REGEX
from variantlib.constants import VARIANT_LABEL_LENGTH
from variantlib.constants import VariantsJsonDict
from variantlib.errors import ValidationError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.models.variant import VariantValidationResult
from variantlib.models.variant_info import PluginUse
from variantlib.models.variant_info import VariantInfo
from variantlib.plugins.loader import PluginLoader
from variantlib.resolver.lib import filter_variants
from variantlib.resolver.lib import sort_and_filter_supported_variants
from variantlib.utils import aggregate_feature_priorities
from variantlib.utils import aggregate_namespace_priorities
from variantlib.utils import aggregate_property_priorities
from variantlib.variant_dist_info import VariantDistInfo
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from variantlib.protocols import VariantNamespace

logger = logging.getLogger(__name__)

__all__ = [
    "VARIANT_LABEL_LENGTH",
    "ProviderConfig",
    "VariantDescription",
    "VariantFeatureConfig",
    "VariantProperty",
    "VariantValidationResult",
    "get_variant_environment_dict",
    "get_variant_label",
    "get_variants_by_priority",
    "make_variant_dist_info",
    "validate_variant",
]


def get_variants_by_priority(
    *,
    variants_json: VariantsJsonDict | VariantsJson,
    venv_python_executable: str | pathlib.Path | None = None,
    enable_optional_plugins: bool | list[VariantNamespace] = False,
) -> list[str]:
    supported_vprops = []
    if not isinstance(variants_json, VariantsJson):
        variants_json = VariantsJson(variants_json)

    venv_python_executable = (
        venv_python_executable
        if venv_python_executable is None
        else pathlib.Path(venv_python_executable)
    )

    with PluginLoader(
        variant_info=variants_json,
        venv_python_executable=venv_python_executable,
        enable_optional_plugins=enable_optional_plugins,
    ) as plugin_loader:
        supported_vprops = list(
            itertools.chain.from_iterable(
                provider_cfg.to_list_of_properties()
                for provider_cfg in plugin_loader.get_supported_configs(
                    known_properties=variants_json.get_known_properties()
                ).values()
            )
        )

    config = VariantConfiguration.get_config()
    label_map = {
        vdesc.hexdigest: label for label, vdesc in variants_json.variants.items()
    }
    # handle the implicit null variant
    label_map.setdefault(VariantDescription([]).hexdigest, NULL_VARIANT_LABEL)

    return [
        label_map[vdesc.hexdigest]
        for vdesc in sort_and_filter_supported_variants(
            list(variants_json.variants.values()),
            supported_vprops,
            namespace_priorities=aggregate_namespace_priorities(
                config.namespace_priorities,
                variants_json.namespace_priorities,
            ),
            feature_priorities=aggregate_feature_priorities(
                config.feature_priorities,
                variants_json.feature_priorities,
            ),
            property_priorities=aggregate_property_priorities(
                config.property_priorities,
                variants_json.property_priorities,
            ),
        )
    ]


def validate_variant(
    variant_desc: VariantDescription,
    variant_info: VariantInfo,
    venv_python_executable: str | pathlib.Path | None = None,
) -> VariantValidationResult:
    """
    Validate all metas in the variant description

    Check whether all metas in the variant description are valid, and return
    a dictionary mapping individual metas into a tri-state variable: True
    indicates that the variant is valid, False that it is not, and None
    that no plugin provides given namespace and therefore the variant cannot
    be verified.
    """

    venv_python_executable = (
        venv_python_executable
        if venv_python_executable is None
        else pathlib.Path(venv_python_executable)
    )

    with PluginLoader(
        variant_info=variant_info,
        venv_python_executable=venv_python_executable,
        enable_optional_plugins=True,
        filter_plugins=list({vprop.namespace for vprop in variant_desc.properties}),
        include_build_plugins=True,
    ) as plugin_loader:
        return plugin_loader.validate_properties(properties=variant_desc.properties)


def make_variant_dist_info(
    vdesc: VariantDescription,
    variant_info: VariantInfo | None = None,
    variant_label: str | None = None,
    expand_build_plugin_properties: bool = True,
    venv_python_executable: str | pathlib.Path | None = None,
) -> str:
    """
    Return the data for *.dist-info/{VARIANT_DIST_INFO_FILENAME} (as str)

    vdesc provides the description for the current variant.

    variant_info provides the common variant information (taken e.g. from
    pyproject.toml). If not specified, an empty variant information is used
    instead.

    variant_label specifies the variant label to use. If not specified,
    the default of variant hash is used.

    If expand_build_plugin_properties is True, then default-priorities
    for plugins with plugin-use == "build" will be filled with the current
    list of supported properties.
    """

    # If we have been parsed VariantInfo, convert it to DistMetadata.
    # If not, start with an empty class.
    if variant_info is None:
        variant_info = VariantInfo()
    variant_json = VariantDistInfo(variant_info)
    variant_json.variant_desc = vdesc
    variant_json.variant_label = get_variant_label(vdesc, variant_label)

    if expand_build_plugin_properties:
        namespaces = {vprop.namespace for vprop in vdesc.properties}
        build_namespaces = {
            ns
            for ns in namespaces
            if ns in variant_info.providers
            and variant_info.providers[ns].plugin_use == PluginUse.BUILD
        }
        if build_namespaces:
            venv_python_executable = (
                venv_python_executable
                if venv_python_executable is None
                else pathlib.Path(venv_python_executable)
            )

            with PluginLoader(
                variant_info=variant_info,
                venv_python_executable=venv_python_executable,
                enable_optional_plugins=True,
                filter_plugins=list(build_namespaces),
                include_build_plugins=True,
            ) as plugin_loader:
                configs = plugin_loader.get_supported_configs(
                    known_properties=vdesc.properties
                ).values()

            for config in configs:
                if config.namespace not in build_namespaces:
                    continue
                for vfeat in config.configs:
                    feature_prios = variant_json.feature_priorities.setdefault(
                        config.namespace, []
                    )
                    prop_prios = variant_json.property_priorities.setdefault(
                        config.namespace, {}
                    ).setdefault(vfeat.name, [])
                    if vfeat.name not in feature_prios:
                        feature_prios.append(vfeat.name)
                    for value in vfeat.values:
                        if value not in prop_prios:
                            prop_prios.append(value)

        # Validate that we did not end up using an unsupported property.
        # This could happen in two cases:
        # 1. validate_variant() was not called.
        # 2. The plugin's get_supported_configs() does not match its
        #    validate_property() behavior.
        # Both are invalid, therefore we just raise an exception.
        for vprop in vdesc.properties:
            if vprop.namespace not in build_namespaces:
                continue
            if (
                vprop.feature not in variant_json.feature_priorities[vprop.namespace]
                or vprop.value
                not in variant_json.property_priorities[vprop.namespace][vprop.feature]
            ):
                raise ValidationError(
                    f"Property {vprop.to_str()!r} is not installable according to the "
                    "respective provider plugin; is plugin-use == 'build' valid for "
                    "this plugin?"
                )

    return variant_json.to_str()


def check_variant_supported(
    *,
    vdesc: VariantDescription | None = None,
    variant_info: VariantInfo,
    venv_python_executable: str | pathlib.Path | None = None,
    enable_optional_plugins: bool | list[VariantNamespace] = False,
) -> bool:
    """Check if variant description is supported

    Returns True if the variant description is supported.

    If `vdesc` is provided, it is tested. Otherwise, `variant_info` must be
    a `DistMetadata` and variant description is inferred from it.
    """

    if vdesc is None:
        if variant_info is None or not isinstance(variant_info, VariantsJson):
            raise TypeError("vdesc or variant_info=VariantsJson(...) must be provided")
        if len(variant_info.variants) != 1:
            raise ValueError(
                "variant_info=VariantsJson(...) must describe exactly one variant"
            )
        vdesc = next(iter(variant_info.variants.values()))

    venv_python_executable = (
        venv_python_executable
        if venv_python_executable is None
        else pathlib.Path(venv_python_executable)
    )

    with PluginLoader(
        variant_info=variant_info,
        venv_python_executable=venv_python_executable,
        enable_optional_plugins=enable_optional_plugins,
    ) as plugin_loader:
        supported_vprops = list(
            itertools.chain.from_iterable(
                provider_cfg.to_list_of_properties()
                for provider_cfg in plugin_loader.get_supported_configs(
                    known_properties=vdesc.properties
                ).values()
            )
        )

    VariantConfiguration.get_config()

    return bool(
        list(
            filter_variants(
                vdescs=[vdesc],
                allowed_properties=supported_vprops,
            )
        )
    )


def get_variant_environment_dict(
    variant_desc: VariantDescription,
) -> dict[str, set[str]]:
    """Get the dict for packaging Marker.evaluate()"""

    return {
        "variant_namespaces": {vprop.namespace for vprop in variant_desc.properties},
        "variant_features": {
            vprop.feature_object.to_str() for vprop in variant_desc.properties
        },
        "variant_properties": {vprop.to_str() for vprop in variant_desc.properties},
    }


def get_variant_label(
    variant_desc: VariantDescription,
    custom_label: str | None = None,
) -> str:
    """
    Get the label for the specified variant

    Get the label corresponding to `variant_desc`. If `custom_label`
    is provided, validate it and use it. If `custom_label` is invalid,
    raises a `ValidationError`.
    """

    if custom_label is None:
        return (
            NULL_VARIANT_LABEL
            if variant_desc.is_null_variant()
            else variant_desc.hexdigest
        )

    if variant_desc.is_null_variant():
        if custom_label != NULL_VARIANT_LABEL:
            raise ValidationError(
                f"Null variant must always use {NULL_VARIANT_LABEL!r} label"
            )
    elif custom_label == NULL_VARIANT_LABEL:
        raise ValidationError(
            f"{NULL_VARIANT_LABEL!r} label can be used only for the null variant"
        )
    elif not VALIDATION_VARIANT_LABEL_REGEX.fullmatch(custom_label):
        raise ValidationError(
            f"Invalid variant label: {custom_label!r} "
            f"(must be up to {VARIANT_LABEL_LENGTH} alphanumeric characters)"
        )
    return custom_label
