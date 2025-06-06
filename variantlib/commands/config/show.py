from __future__ import annotations

import argparse
import contextlib
import logging
import sys

import tomlkit
import tomlkit.items

from variantlib import __package_name__
from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import VariantConfiguration
from variantlib.configuration import get_configuration_files

logging.getLogger("variantlib").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def multiline_array(items: list[str]) -> tomlkit.items.Array:
    array = tomlkit.array().multiline(multiline=True)
    array.extend(items)
    return array


def show(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} config show",
        description="CLI interface to interactively show active configuration.",
    )

    parser.add_argument(
        "environment",
        nargs="?",
        choices=[x.name for x in ConfigEnvironments],
        help=(
            "Optionally specify the exact configuration you wish to see. By default "
            "`variantlib` will show the active configuration."
        ),
        default=None,
    )

    parsed_args = parser.parse_args(args)

    source_f = None
    if parsed_args.environment is None:
        with contextlib.suppress(FileNotFoundError):
            source_f = VariantConfiguration.get_config_file()
        # This mode will return the default configuration if the file does not exist
        configuration = VariantConfiguration.get_config()

    else:
        source_f = get_configuration_files()[
            getattr(ConfigEnvironments, parsed_args.environment)
        ]

        # This mode will raise an exception if the file does not exist
        if not source_f.exists():
            raise FileNotFoundError(
                f"The specified configuration [{parsed_args.environment}] file does "
                f"not exist: `{source_f}`."
            )
        configuration = VariantConfiguration.get_config_from_file(source_f)

    doc = tomlkit.document()
    doc.add(tomlkit.comment(f"This file has been sourced from: `{source_f}`"))

    doc.add(tomlkit.nl())
    doc["namespace_priorities"] = multiline_array(configuration.namespace_priorities)

    for namespace, feature_priorities in configuration.feature_priorities.items():
        doc.add(tomlkit.nl())
        doc[tomlkit.key(["feature_priorities", namespace])] = multiline_array(
            feature_priorities
        )

    for namespace, feature_dict in configuration.property_priorities.items():
        for feature, property_priorities in feature_dict.items():
            doc.add(tomlkit.nl())
            doc[tomlkit.key(["property_priorities", namespace, feature])] = (
                multiline_array(property_priorities)
            )

    tomlkit.dump(doc, sys.stdout)
