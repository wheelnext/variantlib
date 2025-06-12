"""This file regroups the public API of the variantlib package."""

from __future__ import annotations

import itertools
import logging
import pathlib
from typing import TYPE_CHECKING

from variantlib.configuration import VariantConfiguration
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.constants import VariantsJsonDict
from variantlib.models.metadata import VariantInfo
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.models.variant import VariantValidationResult
from variantlib.plugins.loader import PluginLoader
from variantlib.resolver.lib import filter_variants
from variantlib.resolver.lib import sort_and_filter_supported_variants
from variantlib.utils import aggregate_feature_priorities
from variantlib.utils import aggregate_namespace_priorities
from variantlib.utils import aggregate_property_priorities
from variantlib.variants_json import VariantsJson
from variantlib.wheel_metadata import VariantDistInfo

if TYPE_CHECKING:
    from variantlib.protocols import VariantFeatureName
    from variantlib.protocols import VariantFeatureValue
    from variantlib.protocols import VariantNamespace

logger = logging.getLogger(__name__)

__all__ = [
    "VARIANT_HASH_LEN",
    "ProviderConfig",
    "VariantDescription",
    "VariantFeatureConfig",
    "VariantProperty",
    "VariantValidationResult",
    "get_variant_environment_dict",
    "get_variant_hashes_by_priority",
    "make_variant_dist_info",
    "validate_variant",
]


def get_variant_hashes_by_priority(
    *,
    variants_json: VariantsJsonDict | VariantsJson,
    use_auto_install: bool = True,
    isolated: bool = True,
    venv_path: str | pathlib.Path | None = None,
    namespace_priorities: list[VariantNamespace] | None = None,
    feature_priorities: dict[VariantNamespace, list[VariantFeatureName]] | None = None,
    property_priorities: dict[
        VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]
    ]
    | None = None,
    forbidden_namespaces: list[VariantNamespace] | None = None,
    forbidden_features: list[str] | None = None,
    forbidden_properties: list[str] | None = None,
) -> list[str]:
    supported_vprops = []
    if not isinstance(variants_json, VariantsJson):
        variants_json = VariantsJson(variants_json)

    venv_path = venv_path if venv_path is None else pathlib.Path(venv_path)

    with PluginLoader(
        variant_nfo=variants_json,
        use_auto_install=use_auto_install,
        isolated=isolated,
        venv_path=venv_path,
    ) as plugin_loader:
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

    config = VariantConfiguration.get_config()

    return [
        vdesc.hexdigest
        for vdesc in sort_and_filter_supported_variants(
            list(variants_json.variants.values()),
            supported_vprops,
            namespace_priorities=aggregate_namespace_priorities(
                namespace_priorities,
                config.namespace_priorities,
                variants_json.namespace_priorities,
            ),
            feature_priorities=aggregate_feature_priorities(
                feature_priorities,
                config.feature_priorities,
                variants_json.feature_priorities,
            ),
            property_priorities=aggregate_property_priorities(
                property_priorities,
                config.property_priorities,
                variants_json.property_priorities,
            ),
            forbidden_namespaces=forbidden_namespaces,
            forbidden_features=_forbidden_features,
            forbidden_properties=_forbidden_properties,
        )
    ]


def validate_variant(
    variant_desc: VariantDescription,
    metadata: VariantInfo,
    use_auto_install: bool = True,
    isolated: bool = True,
    venv_path: str | pathlib.Path | None = None,
) -> VariantValidationResult:
    """
    Validate all metas in the variant description

    Check whether all metas in the variant description are valid, and return
    a dictionary mapping individual metas into a tri-state variable: True
    indicates that the variant is valid, False that it is not, and None
    that no plugin provides given namespace and therefore the variant cannot
    be verified.
    """

    venv_path = venv_path if venv_path is None else pathlib.Path(venv_path)

    with PluginLoader(
        variant_nfo=metadata,
        use_auto_install=use_auto_install,
        isolated=isolated,
        venv_path=venv_path,
    ) as plugin_loader:
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


def make_variant_dist_info(
    vdesc: VariantDescription,
    variant_metadata: VariantInfo | None = None,
) -> str:
    """Return the data for *.dist-info/{VARIANT_DIST_INFO_FILENAME} (as str)"""

    # If we have been parsed VariantInfo, convert it to DistMetadata.
    # If not, start with an empty class.
    if variant_metadata is None:
        variant_metadata = VariantInfo()
    variant_json = VariantDistInfo(variant_metadata)
    variant_json.variant_desc = vdesc

    return variant_json.to_str()


def check_variant_supported(
    *,
    vdesc: VariantDescription | None = None,
    metadata: VariantInfo,
    use_auto_install: bool = True,
    isolated: bool = True,
    venv_path: str | pathlib.Path | None = None,
    forbidden_namespaces: list[VariantNamespace] | None = None,
    forbidden_features: list[str] | None = None,
    forbidden_properties: list[str] | None = None,
) -> bool:
    """Check if variant description is supported

    Returns True if the variant description is supported.

    If `vdesc` is provided, it is tested. Otherwise, `metadata` must be
    a `DistMetadata` and variant description is inferred from it.
    """

    if vdesc is None:
        if metadata is None or not isinstance(metadata, VariantsJson):
            raise TypeError("vdesc or metadata=VariantsJson(...) must be provided")
        if len(metadata.variants) != 1:
            raise ValueError(
                "metadata=VariantsJson(...) must describe exactly one variant"
            )
        vdesc = next(iter(metadata.variants.values()))

    venv_path = venv_path if venv_path is None else pathlib.Path(venv_path)

    with PluginLoader(
        variant_nfo=metadata,
        use_auto_install=use_auto_install,
        isolated=isolated,
        venv_path=venv_path,
    ) as plugin_loader:
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
