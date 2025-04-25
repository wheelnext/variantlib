from __future__ import annotations

import argparse
import email.parser
import email.policy
import json
import logging
import pathlib
import zipfile
from collections import defaultdict

from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_HEADER
from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX
from variantlib.constants import VARIANTS_JSON_PROVIDER_DATA_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.errors import ValidationError
from variantlib.models.provider import ProviderPackage
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generate_index_json(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="generate_index_json",
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
    known_variants: dict[str, VariantDescription] = {}
    known_providers: set[ProviderPackage] = set()

    for wheel in directory.glob("*.whl"):
        # Skip non wheel variants
        if (wheel_info := VALIDATION_WHEEL_NAME_REGEX.fullmatch(wheel.name)) is None:
            raise TypeError(
                f"The file is not a valid python wheel filename: `{wheel.name}`"
            )

        if wheel_info.group("variant_hash") is None:
            logger.debug(
                "Filepath: `%(input_file)s` ... is not a wheel variant.",
                {"input_file": wheel.name},
            )
            continue

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

            # Only valid Wheel Variants need to be processed
            if (
                variant_entries := wheel_metadata.get_all(
                    METADATA_VARIANT_PROPERTY_HEADER
                )
            ) is None:
                logger.warning(
                    "%(wheel)s: This wheel does not declare any `%(key)s`",
                    {"wheel": wheel, "key": METADATA_VARIANT_PROPERTY_HEADER},
                )
                continue

            # ============== Variant Properties Processing ================ #

            vprops = [VariantProperty.from_str(vprop) for vprop in variant_entries]

            try:
                vdesc = VariantDescription(vprops)
            except ValidationError:
                logger.exception(
                    "%(wheel)s has been rejected due to invalid properties. Will be "
                    "ignored.",
                    {"wheel": wheel},
                )
                continue

            if (vhash := vdesc.hexdigest) not in known_variants:
                known_variants[vhash] = vdesc

            # ============== Variant Providers Processing ================ #
            if not (
                wheel_providers := wheel_metadata.get_all(
                    METADATA_VARIANT_PROVIDER_HEADER, []
                )
            ):
                logger.info(
                    "%(wheel)s: did not declare any `%(key)s`",
                    {"wheel": wheel, "key": METADATA_VARIANT_PROVIDER_HEADER},
                )

            for wheel_provider in wheel_providers:
                known_providers.add(ProviderPackage.from_str(wheel_provider))

    sorted_providers = defaultdict(list)
    for provider in known_providers:
        sorted_providers[provider.namespace].append(provider.package_name)

    with (directory / "variants.json").open(mode="w") as f:
        json.dump(
            {
                VARIANTS_JSON_PROVIDER_DATA_KEY: sorted_providers,
                VARIANTS_JSON_VARIANT_DATA_KEY: {
                    vhash: vdesc.to_dict() for vhash, vdesc in known_variants.items()
                },
            },
            f,
            indent=4,
            sort_keys=True,
        )
