from __future__ import annotations

import argparse
import email.parser
import email.policy
import logging
import pathlib
import shutil
import zipfile

from variantlib import __package_name__
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANT_DIST_INFO_FILENAME

logger = logging.getLogger(__name__)

METADATA_POLICY = email.policy.EmailPolicy(
    utf8=True,
    mangle_from_=False,
    refold_source="none",
)


def unmake_variant(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} unmake-variant",
        description="Transform a variant Wheel into a normal Wheel.",
    )

    parser.add_argument(
        "-f",
        "--file",
        dest="input_filepath",
        type=pathlib.Path,
        required=True,
        help="Wheel file to process",
    )

    parser.add_argument(
        "-o",
        "--output-directory",
        type=pathlib.Path,
        required=True,
        help="Output Directory to use to store the Wheel Variant",
    )

    parsed_args = parser.parse_args(args)

    input_filepath: pathlib.Path = parsed_args.input_filepath
    output_directory: pathlib.Path = parsed_args.output_directory

    _unmake_variant(
        input_filepath,
        output_directory,
    )


def _unmake_variant(
    input_filepath: pathlib.Path,
    output_directory: pathlib.Path,
) -> None:
    # Input Validation
    if not input_filepath.is_file():
        raise FileNotFoundError(f"Input Wheel File `{input_filepath}` does not exists.")

    if not output_directory.is_dir():
        raise FileNotFoundError(
            f"Output Directory `{output_directory}` does not exists."
        )

    # Input Validation - Wheel Filename is valid and non variant already.
    wheel_info = VALIDATION_WHEEL_NAME_REGEX.fullmatch(input_filepath.name)

    if (
        wheel_info := VALIDATION_WHEEL_NAME_REGEX.fullmatch(input_filepath.name)
    ) is None:
        raise TypeError(
            f"The file is not a valid python wheel filename: `{input_filepath.name}`"
        )

    if wheel_info.group("variant_hash") is None:
        logger.info(
            "Filepath: `%(input_file)s` ... is a Standard Wheel",
            {"input_file": input_filepath.name},
        )
        return

    # Determine output wheel filename
    output_filepath = output_directory / f"{wheel_info.group('base_wheel_name')}.whl"

    with (
        zipfile.ZipFile(input_filepath, "r") as input_zip,
        zipfile.ZipFile(output_filepath, "w") as output_zip,
    ):
        for file_info in input_zip.infolist():
            components = file_info.filename.split("/", 2)
            is_dist_info = len(components) == 2 and components[0].endswith(".dist-info")

            if is_dist_info and components[1] == VARIANT_DIST_INFO_FILENAME:
                # This is the variant.json file, we skip it.
                continue

            with (
                input_zip.open(file_info, "r") as input_file,
                output_zip.open(file_info, "w") as output_file,
            ):
                if is_dist_info and components[1] == "RECORD":
                    # Update RECORD to remove the checksum.
                    variant_dist_info_path = (
                        f"{components[0]}/{VARIANT_DIST_INFO_FILENAME}"
                    ).encode()
                    for line in input_file:
                        rec_filename, sha256, size = line.split(b",")
                        if rec_filename != variant_dist_info_path:
                            output_file.write(line)
                else:
                    shutil.copyfileobj(input_file, output_file)

    logger.info("Variant Wheel Created: `%s`", output_filepath.resolve())
