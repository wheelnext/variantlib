from __future__ import annotations

import argparse
import email.parser
import email.policy
import json
import logging
import pathlib
import zipfile

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

            if (variant_hash := wheel_metadata.get("Variant-hash")) is None:
                logger.info("`%s`: not a Wheel Variant - Skipping ...", wheel)
                continue
            if (variant_entries := wheel_metadata.get_all("Variant")) is None:
                logger.warning(
                    "%s: Variant-hash present but no Variant property", wheel
                )
                continue

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
        json.dump({"variants": known_variants}, f, indent=4, sort_keys=True)
