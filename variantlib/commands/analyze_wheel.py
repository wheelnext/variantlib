from __future__ import annotations

import argparse
import logging
import pathlib
import sys
import zipfile
from typing import TYPE_CHECKING

from variantlib import __package_name__
from variantlib.api import get_variant_label
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.variant_dist_info import VariantDistInfo

if TYPE_CHECKING:
    from variantlib.models.variant import VariantDescription

logger = logging.getLogger(__name__)


def pretty_print(vdesc: VariantDescription) -> str:
    result_str = f"{'#' * 30} Variant: `{get_variant_label(vdesc)}` {'#' * 29}"
    for vprop in vdesc.properties:
        result_str += f"\n{vprop.to_str()}"
    result_str += f"\n{'#' * 80}\n"
    return result_str


def analyze_wheel(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} analyze-wheel",
        description="Analyze a Wheel file for Variant Information",
    )
    parser.add_argument(
        "-i",
        "--input_file",
        type=pathlib.Path,
        required=True,
        help="Path to the TML file to be validated",
    )

    parsed_args = parser.parse_args(args)

    input_file = pathlib.Path(parsed_args.input_file)

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: `{input_file}`")

    if input_file.suffix != ".whl":
        raise TypeError(f"File must have a `.whl` extension: `{input_file.name}`")

    # Checking if the wheel file is a valid wheel file
    if (wheel_info := VALIDATION_WHEEL_NAME_REGEX.fullmatch(input_file.name)) is None:
        raise TypeError(
            f"The file is not a valid python wheel filename: `{input_file.name}`"
        )

    if (variant_label := wheel_info.group("variant_label")) is None:
        logger.info(
            "Filepath: `%(input_file)s` ... is a Standard Wheel",
            {"input_file": input_file.name},
        )
        return

    logger.info(
        "Filepath: `%(input_file)s` ... is a Wheel Variant - Label: "
        "`%(variant_label)s`",
        {"input_file": input_file.name, "variant_label": variant_label},
    )

    with zipfile.ZipFile(input_file, "r") as zip_file:
        for name in zip_file.namelist():
            components = name.split("/", 2)
            if (
                len(components) == 2
                and components[0].endswith(".dist-info")
                and components[1] == VARIANT_DIST_INFO_FILENAME
            ):
                variant_dist_info = VariantDistInfo(zip_file.read(name), variant_label)
                break
        else:
            raise ValueError(f"Invalid wheel -- no {VARIANT_DIST_INFO_FILENAME} found")

        # We have to flush the logger handlers to ensure that all logs are printed
        for handler in logger.handlers:
            handler.flush()

        # for line in pretty_print(vdesc=vdesc, providers=providers).splitlines():
        for line in pretty_print(vdesc=variant_dist_info.variant_desc).splitlines():
            sys.stdout.write(f"{line}\n")
