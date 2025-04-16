from __future__ import annotations

import argparse
import email.parser
import email.policy
import logging
import os
import pathlib
import re
import tempfile

import wheel.cli.pack as whl_pck
from wheel.cli.unpack import unpack as wheel_unpack

from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.api import set_variant_metadata
from variantlib.api import validate_variant
from variantlib.constants import VARIANT_HASH_LEN
from variantlib.constants import WHEEL_NAME_VALIDATION_REGEX
from variantlib.errors import ValidationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

METADATA_POLICY = email.policy.EmailPolicy(
    utf8=True,
    mangle_from_=False,
    refold_source="none",
)


def wheel_variant_pack(
    directory: str | pathlib.Path,
    dest_dir: str | pathlib.Path,
    variant_hash: str,
    build_number: str | None = None,
) -> str:
    """Repack a previously unpacked wheel directory into a new wheel file.

    The .dist-info/WHEEL file must contain one or more tags so that the target
    wheel file name can be determined.

    This function is heavily taken from:
    https://github.com/pypa/wheel/blob/main/src/wheel/_commands/pack.py#L14

    Minimal changes tried to be applied to make it work with the Variant Hash.

    :param directory: The unpacked wheel directory
    :param dest_dir: Destination directory (defaults to the current directory)
    :param variant_hash: The hash of the variant to be stored
    """

    # Input Validation
    variant_hash_pattern = rf"^[a-fA-F0-9]{{{VARIANT_HASH_LEN}}}$"
    if not re.match(variant_hash_pattern, variant_hash):
        raise ValidationError(f"Invalid Variant Hash Value `{variant_hash}` ...")

    # Find the .dist-info directory
    dist_info_dirs = [
        fn
        for fn in os.listdir(directory)  # noqa: PTH208
        if os.path.isdir(os.path.join(directory, fn)) and whl_pck.DIST_INFO_RE.match(fn)  # noqa: PTH112, PTH118
    ]
    if len(dist_info_dirs) > 1:
        raise whl_pck.WheelError(
            f"Multiple .dist-info directories found in {directory}"
        )
    if not dist_info_dirs:
        raise whl_pck.WheelError(f"No .dist-info directories found in {directory}")

    # Determine the target wheel filename
    dist_info_dir = dist_info_dirs[0]
    name_version = whl_pck.DIST_INFO_RE.match(dist_info_dir).group("namever")

    # Read the tags and the existing build number from .dist-info/WHEEL
    wheel_file_path = os.path.join(directory, dist_info_dir, "WHEEL")  # noqa: PTH118
    with open(wheel_file_path, "rb") as f:  # noqa: PTH123
        info = whl_pck.BytesParser(policy=whl_pck.email.policy.compat32).parse(f)
        tags: list[str] = info.get_all("Tag", [])
        existing_build_number = info.get("Build")

        if not tags:
            raise whl_pck.WheelError(
                f"No tags present in {dist_info_dir}/WHEEL; cannot determine target "
                f"wheel filename"
            )

    # Set the wheel file name and add/replace/remove the Build tag in .dist-info/WHEEL
    build_number = build_number if build_number is not None else existing_build_number
    if build_number is not None:
        del info["Build"]
        if build_number:
            info["Build"] = build_number
            name_version += "-" + build_number

        if build_number != existing_build_number:
            with open(wheel_file_path, "wb") as f:  # noqa: PTH123
                whl_pck.BytesGenerator(f, maxheaderlen=0).flatten(info)

    # Reassemble the tags for the wheel file
    tagline = whl_pck.compute_tagline(tags)

    # Repack the wheel
    wheel_path = os.path.join(dest_dir, f"{name_version}-{tagline}-{variant_hash}.whl")  # noqa: PTH118
    with whl_pck.WheelFile(wheel_path, "w") as wf:
        logging.info(
            "Repacking wheel as `%(wheel_path)s` ...", {"wheel_path": wheel_path}
        )
        wf.write_files(directory)

    return wheel_path


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
    if not wheel_info:
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

    with tempfile.TemporaryDirectory() as _tmpdir:
        tempdir = pathlib.Path(_tmpdir)
        wheel_unpack(input_filepath, tempdir)

        wheel_dir = next(tempdir.iterdir())

        for _dir in wheel_dir.iterdir():
            if _dir.is_dir() and _dir.name.endswith(".dist-info"):
                distinfo_dir = _dir
                break
        else:
            raise FileNotFoundError("Impossible to find the .dist-info directory.")

        if not (metadata_f := distinfo_dir / "METADATA").exists():
            raise FileNotFoundError(metadata_f)

        with metadata_f.open(mode="r+b") as file:
            # Parse the metadata
            metadata_parser = email.parser.BytesParser()
            metadata = metadata_parser.parse(file)

            # Update the metadata
            set_variant_metadata(metadata, vdesc)

            # Move the file pointer to the beginning
            file.seek(0)

            # Write back the serialized metadata
            file.write(metadata.as_bytes(policy=METADATA_POLICY))

            # Truncate the file to remove any remaining old content
            file.truncate()

        dest_whl_path = wheel_variant_pack(
            directory=wheel_dir,
            dest_dir=output_directory,
            variant_hash=vdesc.hexdigest,
        )

        logger.info(
            "Variant Wheel Created: `%s`", pathlib.Path(dest_whl_path).resolve()
        )
