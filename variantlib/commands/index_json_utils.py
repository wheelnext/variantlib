from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_REQUIRES_HEADER
from variantlib.constants import VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VARIANTS_JSON_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANTS_JSON_FEATURE_KEY
from variantlib.constants import VARIANTS_JSON_NAMESPACE_KEY
from variantlib.constants import VARIANTS_JSON_PROPERTY_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_DATA_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.validators import validate_matches_re
from variantlib.validators import validate_requirement_str

if TYPE_CHECKING:
    import pathlib
    from email.message import Message

logger = logging.getLogger(__name__)


def append_variant_info_to_json_file(
    path: pathlib.Path,
    metadata: Message,
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
    data = {}
    modified = False

    # ========== Loading existing file and setting default values ========== #

    if path.exists():
        data = json.loads(path.read_text())

    for key, default_val in [  # type: ignore[var-annotated]
        (VARIANTS_JSON_VARIANT_DATA_KEY, {}),
        (
            VARIANTS_JSON_PROVIDER_DATA_KEY,
            defaultdict(
                lambda: {
                    VARIANTS_JSON_PROVIDER_REQUIRES_KEY: [],
                    VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY: "",
                }
            ),
        ),
        (
            VARIANTS_JSON_DEFAULT_PRIO_KEY,
            {
                VARIANTS_JSON_NAMESPACE_KEY: [],
                VARIANTS_JSON_FEATURE_KEY: [],
                VARIANTS_JSON_PROPERTY_KEY: [],
            },
        ),
    ]:
        data.setdefault(key, default_val)

    # =================== Variant Properties Processing ==================== #

    variant_properties = metadata.get_all(METADATA_VARIANT_PROPERTY_HEADER, [])

    try:
        vprops = [VariantProperty.from_str(vprop) for vprop in variant_properties]
        vdesc = VariantDescription(vprops)
    except ValidationError as e:
        raise ValidationError("Invalid properties found") from e

    if (vhash := vdesc.hexdigest) not in data[VARIANTS_JSON_VARIANT_DATA_KEY]:
        modified = True
        data[VARIANTS_JSON_VARIANT_DATA_KEY][vhash] = vdesc.to_dict()

    # ===================== Variant Default Priorities ===================== #

    pdata = data[VARIANTS_JSON_DEFAULT_PRIO_KEY]
    for source_key, target_key in [
        (
            METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER,
            VARIANTS_JSON_NAMESPACE_KEY,
        ),
        (
            METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER,
            VARIANTS_JSON_FEATURE_KEY,
        ),
        (
            METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER,
            VARIANTS_JSON_PROPERTY_KEY,
        ),
    ]:
        if _value := metadata.get(source_key):
            value = [v.strip() for v in _value.split(",")]
        else:
            value = []

        if not pdata[target_key]:
            modified = True
            pdata[target_key] = value

        elif pdata[target_key] != value:
            raise ValidationError(
                f"Invalid configuration found. `{source_key}` is not consistent. "
                f"Expected: `{data[target_key]}`, Found: `{value}`"
            )

    # ===================== Variant Provider Requires ===================== #

    for provider_req in metadata.get_all(METADATA_VARIANT_PROVIDER_REQUIRES_HEADER, []):
        try:
            match = VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX.fullmatch(provider_req)
            if match is None:
                raise ValidationError("Regex failure")  # noqa: TRY301

            namespace = match.group("namespace").strip()
            req_str = match.group("requirement_str").strip()
            validate_matches_re(namespace, VALIDATION_NAMESPACE_REGEX)
            validate_requirement_str(req_str)

        except (ValidationError, IndexError):
            raise ValidationError(
                f"Invalid `{METADATA_VARIANT_PROVIDER_REQUIRES_HEADER}` value found: "
                f"`{provider_req}`. Expected format: `<namespace>: <requirement_str>`"
            ) from None

        provider_data = data[VARIANTS_JSON_PROVIDER_DATA_KEY][namespace]
        if req_str not in provider_data[VARIANTS_JSON_PROVIDER_REQUIRES_KEY]:
            modified = True
            provider_data[VARIANTS_JSON_PROVIDER_REQUIRES_KEY].append(req_str)

    # Validation:
    # - Every default namespace has to be declared in the providers dictionary
    # - Each provider has to at least have one "requires" entry
    for namespace in data[VARIANTS_JSON_DEFAULT_PRIO_KEY][VARIANTS_JSON_NAMESPACE_KEY]:
        if (
            pdata := data[VARIANTS_JSON_PROVIDER_DATA_KEY].get(namespace)
        ) is None or len(pdata[VARIANTS_JSON_PROVIDER_REQUIRES_KEY]) == 0:
            raise ValidationError(
                "Invalid configuration found. The variant namespace "
                f"`{namespace}` does not provide any installation "
                "requirements. Expected format: `<namespace>: <requirement>`"
            )

    # ===================== Variant Provider Plugin API ===================== #

    for provider_plugin_api in metadata.get_all(
        METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER, []
    ):
        try:
            match = VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX.fullmatch(
                provider_plugin_api
            )
            if match is None:
                raise ValidationError("Regex failure")  # noqa: TRY301

            namespace = match.group("namespace").strip()
            plugin_api_str = match.group("plugin_api").strip()

            # no need to validate namespace or plugin_api_str again
            # as they are already validated in the regex:
            # `VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX`

        except (ValidationError, IndexError):
            raise ValidationError(
                f"Invalid `{VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX}` value "
                "found: `{provider_plugin_api}`. Expected format: "
                "`<namespace>: <plugin-api>`"
            ) from None

        provider_data = data[VARIANTS_JSON_PROVIDER_DATA_KEY][namespace]
        if curr_val := provider_data[VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY]:
            if curr_val != plugin_api_str:
                raise ValidationError(
                    "Invalid configuration found. The plugin-api for the variant "
                    f"namespace `{namespace}` is not consistent. "
                    f"Expected: `{curr_val}`, Found: `{plugin_api_str}`"
                )
            continue

        modified = True
        provider_data[VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY] = plugin_api_str

    # Validation:
    # - Every default namespace has to be declared in the providers dictionary
    # - Each provider has to at least have one "requires" entry
    for namespace in data[VARIANTS_JSON_DEFAULT_PRIO_KEY][VARIANTS_JSON_NAMESPACE_KEY]:
        if (
            pdata := data[VARIANTS_JSON_PROVIDER_DATA_KEY].get(namespace)
        ) is None or len(pdata[VARIANTS_JSON_PROVIDER_REQUIRES_KEY]) == 0:
            raise ValidationError(
                f"Invalid configuration found. The variant namespace `{namespace}` "
                "does not provide any installation requirements. Expected format: "
                "`<namespace>: <requirement>`"
            )

    # ====================== Write to Disk if modified ===================== #
    if modified:
        with path.open(mode="w") as f:
            json.dump(data, f, indent=4, sort_keys=True)
