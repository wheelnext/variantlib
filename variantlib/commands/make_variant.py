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

from variantlib import __package_name__
from variantlib.api import VariantDescription
from variantlib.api import VariantFeature
from variantlib.api import VariantProperty
from variantlib.api import set_variant_metadata
from variantlib.api import validate_variant
from variantlib.constants import VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX
from variantlib.constants import VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.plugins.loader import ManualPluginLoader

logger = logging.getLogger(__name__)

METADATA_POLICY = email.policy.EmailPolicy(
    utf8=True,
    mangle_from_=False,
    refold_source="none",
)


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

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-P",
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
        "--default-namespace-priorities",
        type=lambda prios: prios.split(","),
        default=[],
        help="Comma separated list of namespace priority",
    )

    parser.add_argument(
        "--default-feature-priorities",
        type=lambda prios: [
            VariantFeature.from_str(vfeat) for vfeat in prios.split(",")
        ],
        default=[],
        help="Comma separated list of feature priority",
    )

    parser.add_argument(
        "--default-property-priorities",
        type=lambda prios: [
            VariantProperty.from_str(vprop) for vprop in prios.split(",")
        ],
        default=[],
        help="Comma separated list of property priority",
    )

    parser.add_argument(
        "--provider-requires",
        action="append",
        default=[],
        help=(
            "Variant provider plugin requirement str to install the plugin (can be "
            "specified multiple times)"
        ),
    )

    parser.add_argument(
        "--provider-api",
        action="append",
        default=[],
        help="Variant provider plugin api to load (can be specified multiple times)",
    )

    parsed_args = parser.parse_args(args)

    variant_metadata = VariantMetadata()
    variant_metadata.namespace_priorities = parsed_args.default_namespace_priorities
    for ns in variant_metadata.namespace_priorities:
        if VALIDATION_NAMESPACE_REGEX.fullmatch(ns) is None:
            raise ValueError(f"The following namespace is invalid: `{ns}`")
    variant_metadata.feature_priorities = parsed_args.default_feature_priorities
    variant_metadata.property_priorities = parsed_args.default_property_priorities

    for provider_api in parsed_args.provider_api:
        if (
            match := VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX.fullmatch(
                provider_api
            )
        ) is None:
            raise ValueError(f"The provider plugin-api: `{provider_api}` is not valid")

        if (namespace := match.group("namespace")) in variant_metadata.providers:
            raise ValueError(
                f"The following namespace `{namespace}` already has a declared "
                "plugin-api"
            )

        variant_metadata.providers[namespace] = ProviderInfo(
            requires=[],
            plugin_api=match.group("plugin_api"),
        )

    for provider_req in parsed_args.provider_requires:
        if (
            match := VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX.fullmatch(provider_req)
        ) is None:
            raise ValueError(f"The provider plugin-api: `{provider_req}` is not valid")

        if (namespace := match.group("namespace")) not in variant_metadata.providers:
            raise ValueError(f"The namespace `{namespace}` declares no plugin-api.")

        variant_metadata.providers[namespace].requires.append(
            match.group("requirement_str")
        )

    for namespace, provider_info in variant_metadata.providers.items():
        if not provider_info.requires:
            raise ValueError(
                f"The provider for namespace `{namespace}` declares no requirement"
            )

    if except_ns := set(variant_metadata.namespace_priorities).difference(
        variant_metadata.providers.keys()
    ):
        raise ValueError(
            "Some default namespaces declare no plugin-api and requirement: "
            f"{except_ns}"
        )

    input_filepath: pathlib.Path = parsed_args.input_filepath
    output_directory: pathlib.Path = parsed_args.output_directory

    _make_variant(
        input_filepath,
        output_directory,
        is_null_variant=parsed_args.null_variant,
        properties=parsed_args.properties,
        validate_properties=not parsed_args.skip_plugin_validation,
        variant_metadata=variant_metadata,
    )


def _make_variant(
    input_filepath: pathlib.Path,
    output_directory: pathlib.Path,
    *,
    is_null_variant: bool,
    properties: list[VariantProperty],
    validate_properties: bool = True,
    variant_metadata: VariantMetadata,
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
            plugin_loader = ManualPluginLoader()
            for provider_nfo in variant_metadata.providers.values():
                plugin_loader.load_plugin(provider_nfo.plugin_api)
            # Verify whether the variant properties are valid
            vdesc_valid = validate_variant(vdesc, plugin_loader=plugin_loader)
            if vdesc_valid.invalid_properties:
                raise ValidationError(
                    "The following variant properties are invalid according to the "
                    "plugins: "
                    f"{', '.join(x.to_str() for x in vdesc_valid.invalid_properties)}"
                )
            if vdesc_valid.unknown_properties:
                raise ValidationError(
                    "The following variant properties use namespaces that are not "
                    "provided by any installed plugin: "
                    f"{', '.join(x.to_str() for x in vdesc_valid.unknown_properties)}"
                )
    else:
        # Create a null variant
        vdesc = VariantDescription()

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
                    set_variant_metadata(
                        metadata, vdesc, variant_metadata=variant_metadata
                    )

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
