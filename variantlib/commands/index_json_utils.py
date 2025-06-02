from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from variantlib.errors import ValidationError
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    import pathlib

logger = logging.getLogger(__name__)


def append_variant_info_to_json_file(
    path: pathlib.Path,
    wheel_variant_json: VariantsJson,
) -> None:
    """
    Append variant information to a JSON file.

    Args:
        json_file (pathlib.Path): The path to the JSON file.
        variant (VariantDescription): The variant description object.
        wheel_name (str): The name of the wheel.

    Raises:
        ValidationError: If the JSON file is not valid or if the variant is not valid.
    """
    data = json.loads(path.read_text()) if path.exists() else {"variants": {}}
    variants_json = VariantsJson(data)

    # Merge/update the variant properties
    variants_json.variants.update(wheel_variant_json.variants)

    # Copy the priorities if not set yet -- otherwise verify consistency
    for attribute in (
        "namespace_priorities",
        "feature_priorities",
        "property_priorities",
    ):
        value = getattr(wheel_variant_json, attribute)
        if not (old_value := getattr(variants_json, attribute)):
            setattr(variants_json, attribute, value)
        elif old_value != value:
            raise ValidationError(
                f"Invalid configuration found. `{attribute}` is not consistent. "
                f"Expected: `{old_value}`, Found: `{value}`"
            )

    for namespace, provider_info in wheel_variant_json.providers.items():
        if (old_provider_info := variants_json.providers.get(namespace)) is None:
            # If provider not yet specified, just copy it
            variants_json.providers[namespace] = provider_info
        else:
            # Otherwise, merge requirements and verify consistency
            for req_str in provider_info.requires:
                if req_str not in old_provider_info.requires:
                    old_provider_info.requires.append(req_str)
            if provider_info.enable_if != old_provider_info.enable_if:
                raise ValidationError(
                    "Invalid configuration found. The enable-if for the variant "
                    f"namespace `{namespace}` is not consistent. "
                    f"Expected: `{old_provider_info.enable_if}`, "
                    f"Found: `{provider_info.enable_if}`"
                )
            if provider_info.plugin_api != old_provider_info.plugin_api:
                raise ValidationError(
                    "Invalid configuration found. The plugin-api for the variant "
                    f"namespace `{namespace}` is not consistent. "
                    f"Expected: `{old_provider_info.plugin_api}`, "
                    f"Found: `{provider_info.plugin_api}`"
                )

    path.write_text(variants_json.to_str())
