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

    directory = parsed_args.directory

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: `{directory}`")
    if not directory.is_dir():
        raise NotADirectoryError(f"Directory not found: `{directory}`")

    vprop_parser = email.parser.BytesParser(policy=email.policy.compat32)
    known_variants: dict[str, dict[str, dict[str, str]]] = {}
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
                logger.info("%s: no Variant-hash", wheel)
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

            variant_dict: dict[str, dict[str, str]] = {}
            for variant_entry in variant_entries:
                vprop = VariantProperty.from_str(variant_entry)
                namespace_dict = variant_dict.setdefault(vprop.namespace, {})
                if vprop.feature in namespace_dict:
                    logger.warning(
                        "%(wheel)s: Duplicate feature: %(namespace)s :: %(feature)s",
                        {
                            "wheel": wheel,
                            "namespace": vprop.namespace,
                            "feature": vprop.feature,
                        },
                    )
                namespace_dict[vprop.feature] = vprop.value
                known_namespaces.add(vprop.namespace)

            if (existing_entry := known_variants.get(variant_hash)) is None:
                known_variants[variant_hash] = variant_dict
            elif existing_entry != variant_dict:
                raise ValueError(
                    f"{wheel}: different property assigned to {variant_hash}"
                )

    with directory.joinpath("variants.json").open("w") as f:
        json.dump(
            {
                "providers": providers,
                "variants": known_variants,
            },
            f,
        )
