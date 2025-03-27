from __future__ import annotations

import argparse
import email.parser
import email.policy
import json
import logging
import pathlib
import zipfile

from variantlib.loader import PluginLoader
from variantlib.meta import VariantMeta

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generate_index_json(args) -> None:  # noqa: C901, PLR0912
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

    metadata_parser = email.parser.BytesParser(policy=email.policy.compat32)
    known_variants: dict[str, dict[str, dict[str, str]]] = {}
    known_namespaces = set()

    for wheel in directory.glob("*.whl"):
        with zipfile.ZipFile(wheel, "r") as zip_file:
            for name in zip_file.namelist():
                if name.endswith(".dist-info/METADATA"):
                    with zip_file.open(name) as f:
                        metadata = metadata_parser.parse(f, headersonly=True)
                    break
            else:
                logger.warning("%s: no METADATA file found", wheel)
                continue

            if (variant_hash := metadata.get("Variant-hash")) is None:
                logger.info("%s: no Variant-hash", wheel)
                continue
            if (variant_entries := metadata.get_all("Variant")) is None:
                logger.warning(
                    "%s: Variant-hash present but no Variant metadata", wheel
                )
                continue

            variant_dict: dict[str, dict[str, str]] = {}
            for variant_entry in variant_entries:
                variant_meta = VariantMeta.from_str(variant_entry)
                namespace_dict = variant_dict.setdefault(variant_meta.namespace, {})
                if variant_meta.key in namespace_dict:
                    logger.warning(
                        "%(wheel)s: Duplicate key: %(namespace)s :: %(key)s",
                        {
                            "wheel": wheel,
                            "namespace": variant_meta.namespace,
                            "key": variant_meta.key,
                        },
                    )
                namespace_dict[variant_meta.key] = variant_meta.value
                known_namespaces.add(variant_meta.namespace)

            if (existing_entry := known_variants.get(variant_hash)) is None:
                known_variants[variant_hash] = variant_dict
            elif existing_entry != variant_dict:
                raise ValueError(
                    f"{wheel}: different metadata assigned to {variant_hash}"
                )

    all_plugins = PluginLoader.distribution_names
    provider_requires = set()
    for namespace in known_namespaces:
        if (plugin := all_plugins.get(namespace)) is not None:
            provider_requires.add(plugin)
        else:
            logger.warning("No known plugin matches variant namespace: %s", namespace)
    provider_requires = {
        plugin
        for provider in known_namespaces
        if (plugin := all_plugins.get(provider)) is not None
    }

    with directory.joinpath("variants.json").open("w") as f:
        json.dump(
            {
                "provider-requires": sorted(provider_requires),
                "variants": known_variants,
            },
            f,
        )
