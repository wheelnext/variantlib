"""This file regroups the public API of the variantlib package."""

from __future__ import annotations

import itertools
import logging
import pathlib
from typing import TYPE_CHECKING

from variantlib.configuration import VariantConfiguration
from variantlib.constants import METADATA_ALL_HEADERS
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_HASH_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_REQUIRES_HEADER
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.dist_metadata import DistMetadata
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.models.variant import VariantValidationResult
from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import PluginLoader
from variantlib.plugins.py_envs import AutoPythonEnv
from variantlib.resolver.lib import filter_variants
from variantlib.resolver.lib import sort_and_filter_supported_variants
from variantlib.utils import aggregate_priority_lists
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from email.message import Message

    from variantlib.models.metadata import VariantMetadata


logger = logging.getLogger(__name__)

__all__ = [
    "VARIANT_HASH_LEN",
    "ProviderConfig",
    "VariantDescription",
    "VariantFeatureConfig",
    "VariantProperty",
    "get_variant_hashes_by_priority",
    "set_variant_metadata",
    "validate_variant",
]


def get_variant_hashes_by_priority(
    *,
    variants_json: dict,
    use_auto_install: bool = True,
    venv_path: str | pathlib.Path | None = None,
    namespace_priorities: list[str] | None = None,
    feature_priorities: list[str] | None = None,
    property_priorities: list[str] | None = None,
    forbidden_namespaces: list[str] | None = None,
    forbidden_features: list[str] | None = None,
    forbidden_properties: list[str] | None = None,
) -> list[str]:
    supported_vprops = []
    parsed_variants_json = VariantsJson(variants_json)

    venv_path = venv_path if venv_path is None else pathlib.Path(venv_path)

    with (
        AutoPythonEnv(
            use_auto_install=use_auto_install, isolated=False, venv_path=venv_path
        ) as python_ctx,
        PluginLoader(
            variant_nfo=parsed_variants_json, python_ctx=python_ctx
        ) as plugin_loader,
    ):
        supported_vprops = list(
            itertools.chain.from_iterable(
                provider_cfg.to_list_of_properties()
                for provider_cfg in plugin_loader.get_supported_configs().values()
            )
        )

    _feature_priorities = (
        None
        if feature_priorities is None
        else [VariantFeature.from_str(vfeat) for vfeat in feature_priorities]
    )

    _property_priorities = (
        None
        if property_priorities is None
        else [VariantProperty.from_str(vprop) for vprop in property_priorities]
    )

    _forbidden_features = (
        None
        if forbidden_features is None
        else [VariantFeature.from_str(vfeat) for vfeat in forbidden_features]
    )

    _forbidden_properties = (
        None
        if forbidden_properties is None
        else [VariantProperty.from_str(vprop) for vprop in forbidden_properties]
    )

    config = VariantConfiguration.get_config()

    return [
        vdesc.hexdigest
        for vdesc in sort_and_filter_supported_variants(
            list(parsed_variants_json.variants.values()),
            supported_vprops,
            namespace_priorities=aggregate_priority_lists(
                namespace_priorities,
                config.namespace_priorities,
                parsed_variants_json.namespace_priorities,
            ),
            feature_priorities=aggregate_priority_lists(
                _feature_priorities,
                config.feature_priorities,
                parsed_variants_json.feature_priorities,
            ),
            property_priorities=aggregate_priority_lists(
                _property_priorities,
                config.property_priorities,
                parsed_variants_json.property_priorities,
            ),
            forbidden_namespaces=forbidden_namespaces,
            forbidden_features=_forbidden_features,
            forbidden_properties=_forbidden_properties,
        )
    ]


def validate_variant(
    variant_desc: VariantDescription, plugin_loader: BasePluginLoader
) -> VariantValidationResult:
    """
    Validate all metas in the variant description

    Check whether all metas in the variant description are valid, and return
    a dictionary mapping individual metas into a tri-state variable: True
    indicates that the variant is valid, False that it is not, and None
    that no plugin provides given namespace and therefore the variant cannot
    be verified.
    """

    provider_cfgs = plugin_loader.get_all_configs()

    def _validate_variant(vprop: VariantProperty) -> bool | None:
        provider_cfg = provider_cfgs.get(vprop.namespace)
        if provider_cfg is None:
            return None
        for key_cfg in provider_cfg.configs:
            if key_cfg.name == vprop.feature:
                return vprop.value in key_cfg.values
        return False

    return VariantValidationResult(
        {vprop: _validate_variant(vprop) for vprop in variant_desc.properties}
    )


def set_variant_metadata(
    metadata: Message,
    vdesc: VariantDescription,
    variant_metadata: VariantMetadata | None = None,
) -> None:
    """Set metadata-related keys in metadata email-dict"""

    # Remove old metadata
    for key in METADATA_ALL_HEADERS:
        del metadata[key]

    # Add variant metadata
    for vprop in vdesc.properties:
        metadata[METADATA_VARIANT_PROPERTY_HEADER] = vprop.to_str()
    metadata[METADATA_VARIANT_HASH_HEADER] = vdesc.hexdigest

    # Copy pyproject.toml metadata
    if variant_metadata is not None:
        for namespace, provider_info in variant_metadata.providers.items():
            for requirement in provider_info.requires:
                metadata[METADATA_VARIANT_PROVIDER_REQUIRES_HEADER] = (
                    f"{namespace}: {requirement}"
                )
            metadata[METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER] = (
                f"{namespace}: {provider_info.plugin_api}"
            )

        if variant_metadata.namespace_priorities:
            metadata[METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER] = ", ".join(
                variant_metadata.namespace_priorities
            )
        if variant_metadata.feature_priorities:
            metadata[METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER] = ", ".join(
                x.to_str() for x in variant_metadata.feature_priorities
            )
        if variant_metadata.property_priorities:
            metadata[METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER] = ", ".join(
                x.to_str() for x in variant_metadata.property_priorities
            )


def check_variant_supported(
    *,
    vdesc: VariantDescription | None = None,
    metadata: VariantMetadata,
    use_auto_install: bool = True,
    venv_path: str | pathlib.Path | None = None,
    forbidden_namespaces: list[str] | None = None,
    forbidden_features: list[str] | None = None,
    forbidden_properties: list[str] | None = None,
) -> bool:
    """Check if variant description is supported

    Returns True if the variant description is supported.

    If `vdesc` is provided, it is tested. Otherwise, `metadata` must be
    a `DistMetadata` and variant description is inferred from it.
    """

    if vdesc is None:
        if metadata is None or not isinstance(metadata, DistMetadata):
            raise TypeError("vdesc or metadata=DistMetadata(...) must be provided")
        vdesc = metadata.variant_desc

    venv_path = venv_path if venv_path is None else pathlib.Path(venv_path)

    with (
        AutoPythonEnv(
            use_auto_install=use_auto_install, isolated=False, venv_path=venv_path
        ) as python_ctx,
        PluginLoader(variant_nfo=metadata, python_ctx=python_ctx) as plugin_loader,
    ):
        supported_vprops = list(
            itertools.chain.from_iterable(
                provider_cfg.to_list_of_properties()
                for provider_cfg in plugin_loader.get_supported_configs().values()
            )
        )

    _forbidden_features = (
        None
        if forbidden_features is None
        else [VariantFeature.from_str(vfeat) for vfeat in forbidden_features]
    )

    _forbidden_properties = (
        None
        if forbidden_properties is None
        else [VariantProperty.from_str(vprop) for vprop in forbidden_properties]
    )

    VariantConfiguration.get_config()

    return bool(
        list(
            filter_variants(
                vdescs=[vdesc],
                allowed_properties=supported_vprops,
                forbidden_namespaces=forbidden_namespaces,
                forbidden_features=_forbidden_features,
                forbidden_properties=_forbidden_properties,
            )
        )
    )
