from __future__ import annotations

import argparse
import logging
import pathlib
import zipfile
from collections import defaultdict
from typing import TYPE_CHECKING

from variantlib import __package_name__
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
from variantlib.variant_dist_info import VariantDistInfo

if TYPE_CHECKING:
    from variantlib.variants_json import VariantsJson

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

    output_files: dict[str, VariantsJson] = {}
    seen_variants: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )

    for wheel in directory.glob("*.whl"):
        # Skip non wheel variants
        if (wheel_info := VALIDATION_WHEEL_NAME_REGEX.fullmatch(wheel.name)) is None:
            logger.exception(
                "The file is not a valid python wheel filename: `%(wheel)s`. Skipped",
                {"wheel": wheel.name},
            )
            continue

        if (vlabel := wheel_info.group("variant_label")) is None:
            logger.debug(
                "Filepath: `%(input_file)s` ... is not a wheel variant. Skipping ...",
                {"input_file": wheel.name},
            )
            continue

        logger.info(
            "Processing wheel: `%(wheel)s` with variant label: `%(vlabel)s`",
            {"wheel": wheel.name, "vlabel": vlabel},
        )

        try:
            with zipfile.ZipFile(wheel, "r") as zip_file:
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
                    logger.warning(
                        "%(wheel)s: no %(filename)s file found",
                        {"wheel": wheel, "filename": VARIANT_DIST_INFO_FILENAME},
                    )
                    continue
        except ValidationError as err:
            logger.warning(
                "%(wheel)s: %(err)s",
                {
                    "wheel": wheel,
                    "err": err,
                },
            )
            continue

        namever = wheel_info.group("namever")
        if (variants_json := output_files.get(namever)) is None:
            # Create a new JSON file from the initial wheel.
            output_files[namever] = variant_dist_info
        else:
            try:
                variants_json.merge(variant_dist_info)
            except ValidationError:
                logger.exception(
                    "Failed to process wheel: `%(wheel)s` with variant label: "
                    "`%(vlabel)s`",
                    {"wheel": wheel.name, "vlabel": vlabel},
                )

        seen_variants[namever][variant_dist_info.variant_desc.hexdigest].add(vlabel)

    for namever, variants in seen_variants.items():
        for vhash, labels in variants.items():
            if len(labels) > 1:
                logger.error(
                    "Multiple `%(namever)s` wheels share the same variant properties: "
                    "all of %(labels)s correspond to variant hash `%(vhash)s`",
                    {"namever": namever, "labels": sorted(labels), "vhash": vhash},
                )

    for namever, variants_json in output_files.items():
        path = directory / f"{namever}-variants.json"
        path.write_text(variants_json.to_str())
