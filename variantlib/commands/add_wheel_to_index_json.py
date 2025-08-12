from __future__ import annotations

import argparse
import json
import logging
import pathlib
import zipfile

from variantlib import __package_name__
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
from variantlib.variant_dist_info import VariantDistInfo
from variantlib.variants_json import VariantsJson

logger = logging.getLogger(__name__)


class NotWheelVariantError(ValidationError):
    pass


def add_wheel_to_index_json(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} generate-index-json",
        description="Generate a JSON index of all package variants",
    )

    parser.add_argument(
        "-f",
        "--wheel-file",
        type=pathlib.Path,
        required=True,
        help="Wheel file to add to the Wheel Variant JSON file",
    )

    parser.add_argument(
        "-i",
        "--input-json-file",
        type=pathlib.Path,
        default=None,
        required=False,
        help="Input JSON file to update",
    )

    parser.add_argument(
        "-o",
        "--output-directory",
        type=pathlib.Path,
        required=True,
        help="Output directory to write the JSON file into",
    )

    parser.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        help="Allows overwrite existing `output-json-file` Path. Otherwise, exception.",
    )

    parsed_args = parser.parse_args(args)

    # =============================== INPUT VALIDATION ============================== #

    wheel_file: pathlib.Path = parsed_args.wheel_file
    if not wheel_file.exists() or not wheel_file.is_file():
        raise FileNotFoundError(f"File not found: `{wheel_file}`")

    input_json_file: pathlib.Path | None = parsed_args.input_json_file
    if input_json_file is None:
        logger.info("Creating the Wheel Variant JSON file from scratch ...")

    elif not input_json_file.exists() or not input_json_file.is_file():
        raise FileNotFoundError(
            f"Input Wheel Variant JSON file not found: `{input_json_file}`"
        )

    output_directory: pathlib.Path = parsed_args.output_directory
    if not output_directory.exists() or not output_directory.is_dir():
        raise FileExistsError(f"Output directory `{output_directory}` does not exist.")

    wheel_info = VALIDATION_WHEEL_NAME_REGEX.fullmatch(wheel_file.name)
    if wheel_info is None:
        raise ValidationError(
            f"The file is not a valid Python wheel: `{wheel_file.name}`"
        )

    if (vlabel := wheel_info.group("variant_label")) is None:
        raise NotWheelVariantError(
            f"The file is not a valid Python wheel variant: `{wheel_file.name}`"
        )

    # ==================== Load Existing Wheel Variant JSON file ==================== #

    variant_json: None | VariantsJson = None

    if input_json_file is not None:
        with input_json_file.open(mode="r") as f:
            variant_json = VariantsJson(json.load(f))

    # ======================== Wheel Variant JSON Generation ======================== #

    logger.info(
        "Processing wheel: `%(wheel)s` with variant label: `%(vlabel)s`",
        {"wheel": wheel_file.name, "vlabel": vlabel},
    )

    with zipfile.ZipFile(wheel_file, "r") as zip_file:
        # Find the variant dist-info file
        for name in zip_file.namelist():
            components = name.split("/", 2)
            if (
                len(components) == 2
                and components[0].endswith(".dist-info")
                and components[1] == VARIANT_DIST_INFO_FILENAME
            ):
                variant_dist_info = VariantDistInfo(zip_file.read(name), vlabel)
                break
        else:
            raise FileNotFoundError(
                "%(wheel)s: no %(filename)s file found",
                {"wheel": wheel_file, "filename": VARIANT_DIST_INFO_FILENAME},
            )

    if variant_json is None:
        variant_json = variant_dist_info
    else:
        variant_json.merge(variant_dist_info)

    namever = wheel_info.group("namever")

    output_json_file = output_directory / f"{namever}-variants.json"

    if output_json_file.exists() and not parsed_args.overwrite:
        raise FileExistsError(
            f"Output JSON file already exists: `{output_json_file}`, use `--overwrite` "
            "to proceed."
        )

    output_json_file.write_text(variant_json.to_str())
