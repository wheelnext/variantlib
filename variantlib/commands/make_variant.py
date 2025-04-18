from __future__ import annotations

import argparse
import base64
import email.parser
import email.policy
import hashlib
import logging
import pathlib
import shutil
import zipfile

from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.api import set_variant_metadata
from variantlib.api import validate_variant
from variantlib.constants import WHEEL_NAME_VALIDATION_REGEX
from variantlib.errors import ValidationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

METADATA_POLICY = email.policy.EmailPolicy(
    utf8=True,
    mangle_from_=False,
    refold_source="none",
)


def make_variant(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="make_variant",
        description="Transform a normal Wheel into a Wheel Variant.",
    )

    parser.add_argument(
        "-p",
        "--property",
        dest="properties",
        type=VariantProperty.from_str,
        required=True,
        action="extend",
        nargs="+",
        help=(
            "Variant Properties to add to the Wheel Variant, can be repeated as many "
            "times as needed"
        ),
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

    # Input Validation
    if not input_filepath.is_file():
        raise FileNotFoundError(f"Input Wheel File `{input_filepath}` does not exists.")

    if not output_directory.is_dir():
        raise FileNotFoundError(
            f"Output Directory `{output_directory}` does not exists."
        )

    # Input Validation - Wheel Filename is valid and non variant already.
    wheel_info = WHEEL_NAME_VALIDATION_REGEX.match(input_filepath.name)
    if wheel_info is None:
        raise ValueError(f"{input_filepath.name!r} is not a valid wheel filename.")

    # Transform properties into a VariantDescription
    vdesc = VariantDescription(properties=parsed_args.properties)

    # Verify whether the variant properties are valid
    vdesc_valid = validate_variant(vdesc)
    if vdesc_valid.invalid_properties:
        raise ValidationError(
            "The following variant properties are invalid according to the plugins: "
            f"{', '.join(x.to_str() for x in vdesc_valid.invalid_properties)}"
        )
    if vdesc_valid.unknown_properties:
        raise ValidationError(
            "The following variant properties use namespaces that are not provided "
            "by any installed plugin: "
            f"{', '.join(x.to_str() for x in vdesc_valid.unknown_properties)}"
        )

    # Determine output wheel filename
    output_filepath = (
        output_directory
        / f"{wheel_info.group('base_wheel_name')}-{vdesc.hexdigest}.whl"
    )

    with zipfile.ZipFile(input_filepath, "r") as input_zip:
        # First, find METADATA file
        for filename in input_zip.namelist():
            components = filename.split("/", 2)
            if (
                len(components) == 2
                and components[0].endswith(".dist-info")
                and components[1] == "METADATA"
            ):
                metadata_filename = filename.encode()
                with input_zip.open(filename, "r") as input_file:
                    # Parse the metadata
                    metadata_parser = email.parser.BytesParser()
                    metadata = metadata_parser.parse(input_file)

                    # Update the metadata
                    set_variant_metadata(metadata, vdesc)

                    # Write the serialized metadata
                    new_metadata = metadata.as_bytes(policy=METADATA_POLICY)
                    break
        else:
            raise FileNotFoundError("No *.dist-info/METADATA file found in wheel")

        with zipfile.ZipFile(output_filepath, "w") as output_zip:
            for file_info in input_zip.infolist():
                components = file_info.filename.split("/", 2)
                with (
                    input_zip.open(file_info, "r") as input_file,
                    output_zip.open(file_info, "w") as output_file,
                ):
                    if (
                        len(components) != 2
                        or not components[0].endswith(".dist-info")
                        or components[1] not in ("METADATA", "RECORD")
                    ):
                        shutil.copyfileobj(input_file, output_file)
                    elif components[1] == "METADATA":
                        # Write the new metadata
                        output_file.write(new_metadata)
                    else:
                        # Update RECORD for the new metadata checksum
                        for line in input_file:
                            new_line = line
                            rec_filename, sha256, size = line.split(b",")
                            if rec_filename == metadata_filename:
                                new_sha256 = base64.urlsafe_b64encode(
                                    hashlib.sha256(new_metadata).digest()
                                ).rstrip(b"=")
                                new_line = (
                                    f"{rec_filename.decode()},"
                                    f"sha256={new_sha256.decode()},"
                                    f"{len(new_metadata)}\n"
                                ).encode()
                            output_file.write(new_line)

        logger.info("Variant Wheel Created: `%s`", output_filepath.resolve())
