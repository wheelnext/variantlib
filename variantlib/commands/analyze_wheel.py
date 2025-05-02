from __future__ import annotations

import argparse
import logging
import pathlib
import re
import sys
import zipfile

from variantlib import __package_name__
from variantlib.constants import METADATA_VARIANT_HASH_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

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
        # original_xml_data = xmltodict.parse(zip_file.open("Data.xml").read())
        for name in zip_file.namelist():
            if name.endswith(".dist-info/METADATA"):
                metadata_str = zip_file.open(name).read().decode("utf-8")
                break

        # Extract the hash value
        hash_match = re.search(rf"{METADATA_VARIANT_HASH_HEADER}: (\w+)", metadata_str)
        hash_value = hash_match.group(1) if hash_match else None
        assert hash_value == variant_hash, (
            "Hash value does not match - this variant is not valid"
        )

        # Extract all variant strings
        variant_matches = re.findall(
            rf"{METADATA_VARIANT_PROPERTY_HEADER}: (.+)", metadata_str
        )
        vprop = variant_matches if variant_matches else []

        vdesc = VariantDescription(
            [VariantProperty.from_str(variant) for variant in vprop]
        )

        # Extract all variant provider strings``
        # TODO: REMOVE
        # providers = [
        #     ProviderPackage.from_str(provider_str)
        #     for provider_str in re.findall(
        #         rf"{METADATA_VARIANT_PROVIDER_HEADER}: (.+)", metadata_str
        #     )
        # ]

        # We have to flush the logger handlers to ensure that all logs are printed
        for handler in logger.handlers:
            handler.flush()

        # for line in pretty_print(vdesc=vdesc, providers=providers).splitlines():
        for line in pretty_print(vdesc=vdesc).splitlines():
            sys.stdout.write(f"{line}\n")
