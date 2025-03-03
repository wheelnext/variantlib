import argparse
import email.parser
import email.policy
import json
import logging
import pathlib
import zipfile
from importlib.metadata import entry_points
from typing import Iterable

from variantlib.meta import VariantMeta

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_variant_plugins() -> Iterable[tuple[str, str]]:
    logger.info("Discovering Wheel Variant plugins...")
    plugins = entry_points().select(group="variantlib.plugins")

    seen = set()
    duplicates = set()
    for plugin_name in [plugin.name for plugin in plugins]:
        if plugin_name in seen:
            duplicates.add(plugin_name)
        else:
            seen.add(plugin_name)

    if duplicates:
        logger.warning(
            "Duplicate plugins found: %s - Unpredicatable behavior.", duplicates
        )

    for plugin in plugins:
        try:
            logger.info(
                f"Loading plugin: {plugin.name} - v{plugin.dist.version}"
            )  # noqa: G004
            plugin_class = plugin.load()
            # TODO: is __provider_name__ a public API?
            yield (plugin_class.__provider_name__, plugin.dist.name)
        except Exception:
            logging.exception("An unknown error happened - Ignoring plugin")


def generate_index_json(args):
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
    known_variants = {}
    known_providers = set()

    for wheel in directory.glob("*.whl"):
        with zipfile.ZipFile(wheel, "r") as zip_file:
            for name in zip_file.namelist():
                if name.endswith(".dist-info/METADATA"):
                    with zip_file.open(name) as f:
                        metadata = metadata_parser.parse(f, headersonly=True)
                    break
            else:
                logger.warning(f"{wheel}: no METADATA file found")
                continue

            if (variant_hash := metadata.get("Variant-hash")) is None:
                logger.info(f"{wheel}: no Variant-hash")
                continue
            if (variant_entries := metadata.get_all("Variant")) is None:
                logger.warn(f"{wheel}: Variant-hash present but no Variant metadata")
                continue

            variant_dict = {}
            for variant_entry in variant_entries:
                variant_meta = VariantMeta.from_str(variant_entry)
                provider_dict = variant_dict.setdefault(variant_meta.provider, {})
                if variant_meta.key in provider_dict:
                    logger.warn(
                        f"{wheel}: Duplicate key: {variant_meta.provider} :: {variant_meta.key}"
                    )
                provider_dict[variant_meta.key] = variant_meta.value
                known_providers.add(variant_meta.provider)

            if (existing_entry := known_variants.get(variant_hash)) is None:
                known_variants[variant_hash] = variant_dict
            elif existing_entry != variant_dict:
                raise ValueError(
                    f"{wheel}: different metadata assigned to {variant_hash}"
                )

    all_plugins = dict(get_variant_plugins())
    provider_requires = set()
    for provider in known_providers:
        if (plugin := all_plugins.get(provider)) is not None:
            provider_requires.add(plugin)
        else:
            logger.warning(f"No known plugin matches variant provider: {provider}")
    provider_requires = {
        plugin
        for provider in known_providers
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
