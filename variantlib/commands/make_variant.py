from __future__ import annotations

import argparse
import base64
import hashlib
import logging
import pathlib
import shutil
import sys
import zipfile
from subprocess import CalledProcessError

from variantlib import __package_name__
from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.api import make_variant_dist_info
from variantlib.api import validate_variant
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
from variantlib.pyproject_toml import VariantPyProjectToml

logger = logging.getLogger(__name__)


def make_variant(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} make-variant",
        description="Transform a normal Wheel into a Wheel Variant.",
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

    parser.add_argument(
        "--installer",
        choices=("pip", "uv"),
        help="Installer to use for providers (choices: pip, uv)",
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-p",
        "--property",
        dest="properties",
        type=VariantProperty.from_str,
        action="extend",
        nargs="+",
        help=(
            "Variant Properties to add to the Wheel Variant, can be repeated as many "
            "times as needed"
        ),
        default=[],
    )

    group.add_argument(
        "--null-variant",
        action="store_true",
        help="make the variant a `null variant` - no variant property.",
    )

    parser.add_argument(
        "--skip-plugin-validation",
        action="store_true",
        help="allow to register invalid or unknown variant properties",
    )

    parser.add_argument(
        "--pyproject-toml",
        type=pathlib.Path,
        default="./pyproject.toml",
        help=(
            "pyproject.toml to read variant variant info from (default: "
            "./pyproject.toml)"
        ),
    )

    parsed_args = parser.parse_args(args)

    try:
        pyproject_toml = VariantPyProjectToml.from_path(parsed_args.pyproject_toml)
    except FileNotFoundError:
        parser.error(f"{str(parsed_args.pyproject_toml)!r} does not exist")
    input_filepath: pathlib.Path = parsed_args.input_filepath
    output_directory: pathlib.Path = parsed_args.output_directory

    _make_variant(
        input_filepath,
        output_directory,
        is_null_variant=parsed_args.null_variant,
        properties=parsed_args.properties,
        validate_properties=not parsed_args.skip_plugin_validation,
        variant_info=pyproject_toml,
        installer=parsed_args.installer,
    )


def _make_variant(
    input_filepath: pathlib.Path,
    output_directory: pathlib.Path,
    *,
    is_null_variant: bool,
    properties: list[VariantProperty],
    validate_properties: bool = True,
    variant_info: VariantPyProjectToml,
    installer: str | None = None,
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

    if not is_null_variant:
        # Transform properties into a VariantDescription
        vdesc = VariantDescription(properties=properties)

        if validate_properties:
            from build.env import DefaultIsolatedEnv

            # make it really verbose to make mypy happy
            if installer is None:
                env_factory = DefaultIsolatedEnv()
            elif installer == "pip":
                env_factory = DefaultIsolatedEnv(installer="pip")
            elif installer == "uv":
                env_factory = DefaultIsolatedEnv(installer="uv")
            else:
                raise ValueError(f"unexpected installer={installer}")

            with env_factory as venv:
                try:
                    venv.install(
                        variant_info.get_provider_requires(
                            {vprop.namespace for vprop in vdesc.properties}
                        )
                    )
                except CalledProcessError as err:
                    sys.stderr.write(
                        "Installing variant provider dependencies failed:\n"
                        f"{err.stderr.decode()}"
                    )
                    raise

                # Verify whether the variant properties are valid
                vdesc_valid = validate_variant(
                    vdesc,
                    variant_info=variant_info,
                    use_auto_install=False,
                    venv_path=venv.path,
                )
                if vdesc_valid.invalid_properties:
                    invalid_str = ", ".join(
                        x.to_str() for x in vdesc_valid.invalid_properties
                    )
                    raise ValidationError(
                        "The following variant properties are invalid according to the "
                        f"plugins: {invalid_str}"
                    )
                if vdesc_valid.unknown_properties:
                    unknown_str = ", ".join(
                        x.to_str() for x in vdesc_valid.unknown_properties
                    )
                    raise ValidationError(
                        "The following variant properties use namespaces that are not "
                        f"provided by any installed plugin: {unknown_str}"
                    )
    else:
        # Create a null variant
        vdesc = VariantDescription()

    # Determine output wheel filename
    output_filepath = (
        output_directory
        / f"{wheel_info.group('base_wheel_name')}-{vdesc.hexdigest}.whl"
    )

    with (
        zipfile.ZipFile(input_filepath, "r") as input_zip,
        zipfile.ZipFile(output_filepath, "w") as output_zip,
    ):
        for file_info in input_zip.infolist():
            components = file_info.filename.split("/", 2)
            is_dist_info = len(components) == 2 and components[0].endswith(".dist-info")

            if is_dist_info and components[1] == VARIANT_DIST_INFO_FILENAME:
                # If a wheel dist-info file exists already, discard the existing
                # copy.
                continue

            with input_zip.open(file_info, "r") as input_file:
                if is_dist_info and components[1] == "RECORD":
                    # First, add new dist-info file prior to RECORD (not strictly
                    # required, but a nice convention).
                    dist_info_path = f"{components[0]}/{VARIANT_DIST_INFO_FILENAME}"
                    dist_info_data = make_variant_dist_info(vdesc, variant_info)
                    output_zip.writestr(dist_info_path, dist_info_data)

                    # Update RECORD for the new checksums.
                    with output_zip.open(file_info, "w") as output_file:
                        for line in input_file:
                            new_line = line
                            rec_filename, sha256, size = line.split(b",")
                            # Skip existing hash for the discarded copy.
                            if rec_filename.decode("utf-8") == dist_info_path:
                                continue
                            output_file.write(new_line)

                        # Write hash for the new files.
                        new_sha256 = base64.urlsafe_b64encode(
                            hashlib.sha256(dist_info_data.encode("utf8")).digest()
                        ).rstrip(b"=")
                        output_file.write(
                            (
                                f"{dist_info_path},"
                                f"sha256={new_sha256.decode()},"
                                f"{len(dist_info_data)}\n"
                            ).encode()
                        )
                else:
                    with output_zip.open(file_info, "w") as output_file:
                        shutil.copyfileobj(input_file, output_file)

    logger.info("Variant Wheel Created: `%s`", output_filepath.resolve())
