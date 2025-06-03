from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys
import zipfile
from typing import TYPE_CHECKING

from variantlib import __package_name__
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from variantlib.models.variant import VariantDescription

logger = logging.getLogger(__name__)


def pretty_print(vdesc: VariantDescription) -> str:
    result_str = f"{'#' * 30} Variant: `{vdesc.hexdigest}` {'#' * 29}"
    for vprop in vdesc.properties:
        result_str += f"\n{METADATA_VARIANT_PROPERTY_HEADER}: {vprop.to_str()}"
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

    if (variant_hash := wheel_info.group("variant_hash")) is None:
        logger.info(
            "Filepath: `%(input_file)s` ... is a Standard Wheel",
            {"input_file": input_file.name},
        )
        return

    logger.info(
        "Filepath: `%(input_file)s` ... is a Wheel Variant - Hash: `%(variant_hash)s`",
        {"input_file": input_file.name, "variant_hash": variant_hash},
    )

    with zipfile.ZipFile(input_file, "r") as zip_file:
        for name in zip_file.namelist():
            if name.endswith(f".dist-info/{VARIANT_DIST_INFO_FILENAME}"):
                with zip_file.open(name) as metadata_file:
                    metadata = VariantsJson(json.load(metadata_file))
                break
        else:
            raise ValueError(f"Invalid wheel -- no {VARIANT_DIST_INFO_FILENAME} found")

        if len(metadata.variants) != 1:
            raise ValueError(
                f"Invalid wheel -- {VARIANT_DIST_INFO_FILENAME} specifies "
                f"len(metadata.variants) variants, expected exactly one."
            )
        if variant_hash not in metadata.variants:
            raise ValueError(
                f"Invalid wheel -- {VARIANT_DIST_INFO_FILENAME} specifies "
                f"hash {next(iter(metadata.variants))}, expected {variant_hash}."
            )

        # We have to flush the logger handlers to ensure that all logs are printed
        for handler in logger.handlers:
            handler.flush()

        # for line in pretty_print(vdesc=vdesc, providers=providers).splitlines():
        for line in pretty_print(vdesc=metadata.variants[variant_hash]).splitlines():
            sys.stdout.write(f"{line}\n")
