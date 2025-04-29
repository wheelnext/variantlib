from __future__ import annotations

import email.parser
import email.policy
import logging
import pathlib
import shutil
import tempfile

from wheel.cli.pack import pack as wheel_pack
from wheel.cli.unpack import unpack as wheel_unpack

from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.api import set_variant_metadata
from variantlib.api import validate_variant
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.errors import ValidationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

METADATA_POLICY = email.policy.EmailPolicy(
    utf8=True,
    mangle_from_=False,
    refold_source="none",
)

FILENAME_PATTERNS = [
    "-cu12",
    "_cu12",
    "-cu11",
    "_cu11",
]

VERSION_PATTERNS = [
    "+cpu",
    "+cu118",
    "+cu126",
    "+cu128",
    "+cu11",
    "+cu12",
]


def hack_variant(
    input_filepath: pathlib.Path,
    output_directory: pathlib.Path,
    properties: list[VariantProperty],
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
    if wheel_info is None:
        raise ValueError(f"{input_filepath.name!r} is not a valid wheel filename.")

    # Transform properties into a VariantDescription
    vdesc = VariantDescription(properties=properties)

    # Check if the variant properties are valid if not a null variant
    if properties:
        # Verify whether the variant properties are valid
        vdesc_valid = validate_variant(vdesc)
        if vdesc_valid.invalid_properties:
            raise ValidationError(
                "The following variant properties are invalid according to the "
                "plugins: "
                f"{', '.join(x.to_str() for x in vdesc_valid.invalid_properties)}"
            )
        if vdesc_valid.unknown_properties:
            raise ValidationError(
                "The following variant properties use namespaces that are not provided "
                "by any installed plugin: "
                f"{', '.join(x.to_str() for x in vdesc_valid.unknown_properties)}"
            )

    output_filepath = (
        output_directory
        / f"{wheel_info.group('base_wheel_name')}-{vdesc.hexdigest}.whl"
    )
    f_name = output_filepath.name
    for pattern in [*FILENAME_PATTERNS, *VERSION_PATTERNS]:
        f_name = f_name.replace(pattern, "")
    output_filepath = output_filepath.with_name(f_name)

    if output_filepath.exists():
        return

    with tempfile.TemporaryDirectory() as _tmpdir:
        tempdir = pathlib.Path(_tmpdir)
        wheel_unpack(str(input_filepath), tempdir)

        unpacked_dir = next(tempdir.iterdir())
        assert unpacked_dir.is_dir()

        distinfo_dir = None
        for _dir in unpacked_dir.iterdir():
            if _dir.is_dir() and _dir.name.endswith(".dist-info"):
                distinfo_dir = _dir
                break
        else:
            raise FileNotFoundError("No *.dist-info directory found in unpacked wheel")

        new_dir_name = distinfo_dir.name
        for pattern in [*FILENAME_PATTERNS, *VERSION_PATTERNS]:
            new_dir_name = new_dir_name.replace(pattern, "")

        if new_dir_name != distinfo_dir.name:
            distinfo_dir = distinfo_dir.rename(distinfo_dir.with_name(new_dir_name))

        metadata_filename = distinfo_dir / "METADATA"
        if not metadata_filename.is_file():
            raise FileNotFoundError("No METADATA file found in unpacked wheel")

        with metadata_filename.open(mode="rb") as input_file:
            # Parse the metadata
            metadata_parser = email.parser.BytesParser()
            metadata = metadata_parser.parse(input_file)

            # Set the new package name if provided
            package_name = metadata["Name"]
            for pattern in FILENAME_PATTERNS:
                package_name = package_name.replace(pattern, "")
            # print(f"{package_name=}")
            if package_name != metadata["Name"]:
                metadata.replace_header("Name", package_name)

            package_version = metadata["Version"].split("+")[0]
            # print(f"{package_version=}")
            if package_version != metadata["Version"]:
                metadata.replace_header("Version", metadata["Version"].split("+")[0])

            deps = metadata.get_all("Requires-Dist", [])
            del metadata["Requires-Dist"]
            for dep in deps:
                # print(f"BEFORE: {dep}")
                for pattern in [*FILENAME_PATTERNS, *VERSION_PATTERNS]:
                    dep = dep.replace(pattern, "")  # noqa: PLW2901
                # print(f"AFTER:  {dep}\n")
                metadata["Requires-Dist"] = dep

            # Update the metadata
            set_variant_metadata(metadata, vdesc)

        with metadata_filename.open(mode="wb") as output_file:
            output_file.write(metadata.as_bytes(policy=METADATA_POLICY))

        wheel_pack(unpacked_dir, _tmpdir, None)
        whl_f = next(pathlib.Path(_tmpdir).glob("*.whl"))
        wheel_info = VALIDATION_WHEEL_NAME_REGEX.fullmatch(whl_f.name)
        if wheel_info is None:
            raise ValueError(f"{input_filepath.name!r} is not a valid wheel filename.")

        output_filepath = (
            output_directory
            / f"{wheel_info.group('base_wheel_name')}-{vdesc.hexdigest}.whl"
        )

        shutil.copy(whl_f, output_filepath)
        logger.info("Variant Wheel Created: `%s`", output_filepath.resolve())
