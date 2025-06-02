from __future__ import annotations

import argparse
import json
import logging
import pathlib
import zipfile

from variantlib import __package_name__
from variantlib.commands.index_json_utils import append_variant_info_to_json_file
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
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

    seen_namevers = set()

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

        if (namever := wheel_info.group("namever")) not in seen_namevers:
            # Clean old JSON file if it exists at first encounter
            # This is to avoid appending to an existing file
            path = directory / f"{namever}-variants.json"
            path.unlink(missing_ok=True)
            seen_namevers.add(namever)
            logger.info("Updating: `%(path)s`", {"path": path})

        logger.info(
            "Processing wheel: `%(wheel)s` with variant hash: `%(vhash)s`",
            {"wheel": wheel.name, "vhash": vhash},
        )

        with zipfile.ZipFile(wheel, "r") as zip_file:
            # Find the METADATA file
            for name in zip_file.namelist():
                if name.endswith(f".dist-info/{VARIANT_DIST_INFO_FILENAME}"):
                    with zip_file.open(name) as metadata_file:
                        wheel_metadata = VariantsJson(json.load(metadata_file))
                    break
            else:
                logger.warning(
                    "%(wheel)s: no %(filename)s file found",
                    {"wheel": wheel, "filename": VARIANT_DIST_INFO_FILENAME},
                )
                continue

            if len(wheel_metadata.variants) != 1:
                logger.warning(
                    "%(wheel)s: %(filename)s specifies %(num_variants)d variants, "
                    "expected exactly one",
                    {
                        "wheel": wheel,
                        "filename": VARIANT_DIST_INFO_FILENAME,
                        "num_variants": len(wheel_metadata.variants),
                    },
                )
                continue

            try:
                append_variant_info_to_json_file(
                    path=directory / f"{namever}-variants.json",
                    wheel_variant_json=wheel_metadata,
                )
            except ValidationError:
                logger.exception(
                    "Failed to process wheel: `%(wheel)s` with variant hash: "
                    "`%(vhash)s`",
                    {"wheel": wheel.name, "vhash": vhash},
                )
                continue
