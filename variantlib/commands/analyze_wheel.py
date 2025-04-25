from __future__ import annotations

import argparse
import logging
import pathlib
import re
import zipfile

from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def analyze_wheel(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="analyze_wheel", description="Analyze a Wheel file for Variant Information"
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
                vprop_str = zip_file.open(name).read().decode("utf-8")
                break

        # Extract the hash value
        hash_match = re.search(r"Variant-hash: (\w+)", vprop_str)
        hash_value = hash_match.group(1) if hash_match else None
        assert hash_value == variant_hash, (
            "Hash value does not match - this variant is not valid"
        )

        # Extract all variant strings
        variant_matches = re.findall(r"Variant: (.+)", vprop_str)
        vprop = variant_matches if variant_matches else []

        vdesc = VariantDescription(
            [VariantProperty.from_str(variant) for variant in vprop]
        )

        logger.info(vdesc.pretty_print())
