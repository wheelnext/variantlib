from __future__ import annotations

import argparse
import email.parser
import email.policy
import json
import logging
import pathlib
import zipfile
from collections import defaultdict

from variantlib import __package_name__
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_ENTRYPOINT_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_REQUIRES_HEADER
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PROVIDER_ENTRYPOINT_REGEX
from variantlib.constants import VALIDATION_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANTS_JSON_DEFAULT_PRIO_FEATURE_KEY
from variantlib.constants import VARIANTS_JSON_DEFAULT_PRIO_NAMESPACE_KEY
from variantlib.constants import VARIANTS_JSON_DEFAULT_PRIO_PROPERTY_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_DATA_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_ENTRY_POINT_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.validators import validate_matches_re
from variantlib.validators import validate_requirement_str

logger = logging.getLogger(__name__)


def generate_index_json(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} generate-index-json",
        description="Generate a JSON index of all package variants",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=pathlib.Path,
        required=True,
        help="Directory to process",
    )

    parsed_args = parser.parse_args(args)

    directory: pathlib.Path = parsed_args.directory

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: `{directory}`")
    if not directory.is_dir():
        raise NotADirectoryError(f"Directory not found: `{directory}`")

    vprop_parser = email.parser.BytesParser(policy=email.policy.compat32)

    for wheel in directory.glob("*.whl"):
        # Skip non wheel variants
        if (wheel_info := VALIDATION_WHEEL_NAME_REGEX.fullmatch(wheel.name)) is None:
            logger.exception(
                "The file is not a valid python wheel filename: `%(wheel)s`. Skipped",
                {"wheel": wheel.name},
            )
            continue

        if (vhash := wheel_info.group("variant_hash")) is None:
            logger.debug(
                "Filepath: `%(input_file)s` ... is not a wheel variant. Skipping ...",
                {"input_file": wheel.name},
            )
            continue

        logger.info(
            "Processing wheel: `%(wheel)s` with variant hash: `%(vhash)s`",
            {"wheel": wheel.name, "vhash": vhash},
        )

        with zipfile.ZipFile(wheel, "r") as zip_file:
            # Find the METADATA file
            for name in zip_file.namelist():
                if name.endswith(".dist-info/METADATA"):
                    with zip_file.open(name) as f:
                        wheel_metadata = vprop_parser.parse(f, headersonly=True)
                    break

            else:
                logger.warning("%s: no METADATA file found", wheel)
                continue

            data = {}
            modified = False
            pkg_version = wheel_metadata.get("Version")

            # ========== Loading existing file and setting default values ========== #

            if (variant_fp := directory / f"variants-{pkg_version}.json").exists():
                data = json.loads(variant_fp.read_text())

            for key, default_val in [  # type: ignore[var-annotated]
                (VARIANTS_JSON_VARIANT_DATA_KEY, {}),
                (
                    VARIANTS_JSON_PROVIDER_DATA_KEY,
                    defaultdict(
                        lambda: {
                            VARIANTS_JSON_PROVIDER_REQUIRES_KEY: [],
                            VARIANTS_JSON_PROVIDER_ENTRY_POINT_KEY: "",
                        }
                    ),
                ),
                (VARIANTS_JSON_DEFAULT_PRIO_NAMESPACE_KEY, []),
                (VARIANTS_JSON_DEFAULT_PRIO_FEATURE_KEY, []),
                (VARIANTS_JSON_DEFAULT_PRIO_PROPERTY_KEY, []),
            ]:
                data.setdefault(key, default_val)

            # =================== Variant Properties Processing ==================== #

            variant_properties = wheel_metadata.get_all(
                METADATA_VARIANT_PROPERTY_HEADER, []
            )

            try:
                vprops = [
                    VariantProperty.from_str(vprop) for vprop in variant_properties
                ]
                vdesc = VariantDescription(vprops)
            except ValidationError:
                logger.exception(
                    "%(wheel)s has been rejected due to invalid properties. Will be "
                    "ignored.",
                    {"wheel": wheel},
                )
                continue

            if (vhash := vdesc.hexdigest) not in data[VARIANTS_JSON_VARIANT_DATA_KEY]:
                modified = True
                data[VARIANTS_JSON_VARIANT_DATA_KEY][vhash] = vdesc.to_dict()

            # ===================== Variant Provider Requires ===================== #

            error = False
            for provider_req in wheel_metadata.get_all(
                METADATA_VARIANT_PROVIDER_REQUIRES_HEADER, []
            ):
                if not (
                    match := VALIDATION_PROVIDER_REQUIRES_REGEX.fullmatch(provider_req)
                ):
                    logger.error(
                        "%(wheel)s has an invalid `%(key)s` value: `%(value)s`. "
                        "Expected format: `<namespace>: <requirement_str>`",
                        {
                            "wheel": wheel,
                            "key": METADATA_VARIANT_PROVIDER_REQUIRES_HEADER,
                            "value": provider_req,
                        },
                    )
                    error = True
                    break

                namespace = match.group("namespace").strip()
                req_str = match.group("requirement_str").strip()

                try:
                    validate_matches_re(namespace, VALIDATION_NAMESPACE_REGEX)
                    validate_requirement_str(req_str)
                except ValidationError:
                    logger.exception(
                        "%(wheel)s has an invalid `%(key)s` value: `%(value)s`. "
                        "Expected format: `<namespace>: <requirement_str>`",
                        {
                            "wheel": wheel,
                            "key": METADATA_VARIANT_PROVIDER_REQUIRES_HEADER,
                            "value": provider_req,
                        },
                    )
                    error = True
                    break

                provider_data = data[VARIANTS_JSON_PROVIDER_DATA_KEY][namespace]
                if req_str not in provider_data[VARIANTS_JSON_PROVIDER_REQUIRES_KEY]:
                    modified = True
                    provider_data[VARIANTS_JSON_PROVIDER_REQUIRES_KEY].append(req_str)

            if error:
                continue

            # Validation:
            # - Every default namespace has to be declared in the providers dictionary
            # - Each provider has to at least have one "requires" entry
            for namespace in data[VARIANTS_JSON_DEFAULT_PRIO_NAMESPACE_KEY]:
                if (
                    pdata := data[VARIANTS_JSON_PROVIDER_DATA_KEY].get(namespace)
                ) is None or len(pdata[VARIANTS_JSON_PROVIDER_REQUIRES_KEY]) == 0:
                    logger.error(
                        "%(wheel)s has an invalid configuration. The variant namespace "
                        "`%(namespace)s` does not provide any installation "
                        "requirements. Expected format: `<namespace>: <requirement>`",
                        {"wheel": wheel, "namespace": namespace},
                    )
                    error = True
                    break

            # ===================== Variant Provider Entry-Point ===================== #

            error = False
            for provider_entrypoint in wheel_metadata.get_all(
                METADATA_VARIANT_PROVIDER_ENTRYPOINT_HEADER, []
            ):
                if not (
                    match := VALIDATION_PROVIDER_ENTRYPOINT_REGEX.fullmatch(
                        provider_entrypoint
                    )
                ):
                    logger.error(
                        "%(wheel)s has an invalid `%(key)s` value: `%(value)s`. "
                        "Expected format: `<namespace>: <entry-point>`",
                        {
                            "wheel": wheel,
                            "key": METADATA_VARIANT_PROVIDER_ENTRYPOINT_HEADER,
                            "value": provider_entrypoint,
                        },
                    )
                    error = True
                    break

                namespace = match.group("namespace").strip()
                entrypoint_str = match.group("entrypoint").strip()

                try:
                    validate_matches_re(namespace, VALIDATION_NAMESPACE_REGEX)
                except ValidationError:
                    logger.exception(
                        "%(wheel)s has an invalid `%(key)s` value: `%(value)s`. "
                        "Expected format: `<namespace>: <entry-point>`",
                        {
                            "wheel": wheel,
                            "key": METADATA_VARIANT_PROVIDER_ENTRYPOINT_HEADER,
                            "value": provider_entrypoint,
                        },
                    )
                    error = True
                    break

                provider_data = data[VARIANTS_JSON_PROVIDER_DATA_KEY][namespace]
                if curr_val := provider_data[VARIANTS_JSON_PROVIDER_ENTRY_POINT_KEY]:
                    if curr_val != entrypoint_str:
                        logger.error(
                            (
                                "The entry-point for the variant namespace `%(ns)s` in "
                                "the wheel `%(wheel)s` is not consistent. "
                                "Expected: `%(expected)s`, Found: `%(found)s`"
                            ),
                            {
                                "ns": namespace,
                                "wheel": wheel,
                                "expected": curr_val,
                                "found": entrypoint_str,
                            },
                        )
                        error = True
                        break
                    continue

                provider_data[VARIANTS_JSON_PROVIDER_ENTRY_POINT_KEY] = entrypoint_str
                modified = True

            if error:
                continue

            # Validation:
            # - Every default namespace has to be declared in the providers dictionary
            # - Each provider has to at least have one "requires" entry
            for namespace in data[VARIANTS_JSON_DEFAULT_PRIO_NAMESPACE_KEY]:
                if (
                    pdata := data[VARIANTS_JSON_PROVIDER_DATA_KEY].get(namespace)
                ) is None or len(pdata[VARIANTS_JSON_PROVIDER_REQUIRES_KEY]) == 0:
                    logger.error(
                        "%(wheel)s has an invalid configuration. The variant namespace "
                        "`%(namespace)s` does not provide any installation "
                        "requirements. Expected format: `<namespace>: <requirement>`",
                        {"wheel": wheel, "namespace": namespace},
                    )
                    error = True
                    break

            # ===================== Variant Default Priorities ===================== #

            for source_key, target_key in [
                (
                    METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER,
                    VARIANTS_JSON_DEFAULT_PRIO_NAMESPACE_KEY,
                ),
                (
                    METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER,
                    VARIANTS_JSON_DEFAULT_PRIO_FEATURE_KEY,
                ),
                (
                    METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER,
                    VARIANTS_JSON_DEFAULT_PRIO_PROPERTY_KEY,
                ),
            ]:
                if _value := wheel_metadata.get(source_key):
                    value = [v.strip() for v in _value.split(",")]
                else:
                    value = []

                if not data[target_key]:
                    modified = True
                    data[target_key] = value

                elif data[target_key] != value:
                    logger.error(
                        (
                            "`%(key)s` in the wheel `%(wheel)s` is not consistent. "
                            "Expected: `%(expected)s`, Found: `%(found)s`"
                        ),
                        {
                            "key": source_key,
                            "wheel": wheel,
                            "expected": data[target_key],
                            "found": value,
                        },
                    )

            # ====================== Write to Disk if modified ===================== #

            if modified:
                with variant_fp.open(mode="w") as f:
                    json.dump(data, f, indent=4, sort_keys=True)
