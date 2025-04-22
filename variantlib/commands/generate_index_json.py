from __future__ import annotations

import argparse
import email.parser
import email.policy
import json
import logging
import pathlib
import zipfile

from variantlib.constants import METADATA_VARIANT_HASH_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_HEADER
from variantlib.constants import VARIANTS_JSON_PROVIDER_DATA_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.errors import ValidationError
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
    known_namespaces = set()
    providers: dict[str, str] = {}

    for wheel in directory.glob("*.whl"):
        with zipfile.ZipFile(wheel, "r") as zip_file:
            for name in zip_file.namelist():
                if name.endswith(".dist-info/METADATA"):
                    with zip_file.open(name) as f:
                        wheel_metadata = vprop_parser.parse(f, headersonly=True)
                    break

            else:
                logger.warning("%s: no METADATA file found", wheel)
                continue

            if (
                variant_hash := wheel_metadata.get(METADATA_VARIANT_HASH_HEADER)
            ) is None:
                logger.debug("%s: not a Wheel Variant. Skipping ...", wheel)
                continue

            if (
                variant_entries := wheel_metadata.get_all(
                    METADATA_VARIANT_PROPERTY_HEADER
                )
            ) is None:
                logger.warning(
                    "%s: Variant-hash present but no Variant property", wheel
                )
                continue

            if (
                wheel_providers := wheel_metadata.get_all(
                    METADATA_VARIANT_PROVIDER_HEADER
                )
            ) is None:
                logger.info("%s: no Variant-provider", wheel)

            else:
                for wheel_provider in wheel_providers:
                    ns, _, provider = wheel_provider.partition(",")
                    ns = ns.strip()
                    provider = provider.strip()
                    if not ns or not provider:
                        raise ValueError(
                            f"{wheel}: Invalid {METADATA_VARIANT_PROVIDER_HEADER}: "
                            f"{wheel_provider}"
                        )
                    if providers.setdefault(ns, provider) != provider:
                        raise KeyError(
                            f"Conflicting providers found for namespace {ns}: "
                            f"{providers[ns]} and {provider}"
                        )

            vprops = [VariantProperty.from_str(vprop) for vprop in variant_entries]
            for vprop in vprops:
                known_namespaces.add(vprop.namespace)

            try:
                vdesc = VariantDescription(vprops)
                if vdesc.hexdigest != variant_hash:
                    logger.error(
                        "%(wheel)s has been rejected due to a variant hash mismatch: "
                        "Found: `%(vhash_found)s` != Calculated: `%(vhash_calc)s`. "
                        "Will be ignored.",
                        {
                            "wheel": wheel,
                            "vhash_found": variant_hash,
                            "vhash_calc": vdesc.hexdigest,
                        },
                    )
                    continue

            except ValidationError:
                logger.exception(
                    "%(wheel)s has been rejected due to invalid properties. Will be "
                    "ignored.",
                    {"wheel": wheel},
                )
                continue

            if vdesc.hexdigest not in known_variants:
                known_variants[variant_hash] = vdesc

    with directory.joinpath("variants.json").open("w") as f:
        json.dump(
            {
                VARIANTS_JSON_PROVIDER_DATA_KEY: providers,
                VARIANTS_JSON_VARIANT_DATA_KEY: {
                    vhash: vdesc.to_dict() for vhash, vdesc in known_variants.items()
                },
            },
            f,
            indent=4,
            sort_keys=True,
        )
