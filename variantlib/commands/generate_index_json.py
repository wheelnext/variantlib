from __future__ import annotations

import argparse
import email.parser
import email.policy
import logging
import pathlib
import zipfile

from variantlib import __package_name__
from variantlib.commands.index_json_utils import append_variant_info_to_json_file
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.errors import ValidationError

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
                if name.endswith(".dist-info/METADATA"):
                    with zip_file.open(name) as f:
                        wheel_metadata = vprop_parser.parse(f, headersonly=True)
                    break

            else:
                logger.warning("%s: no METADATA file found", wheel)
                continue

            try:
                append_variant_info_to_json_file(
                    path=directory / f"{namever}-variants.json",
                    metadata=wheel_metadata,
                )
            except ValidationError:
                logger.exception(
                    "Failed to process wheel: `%(wheel)s` with variant hash: "
                    "`%(vhash)s`",
                    {"wheel": wheel.name, "vhash": vhash},
                )
                continue
