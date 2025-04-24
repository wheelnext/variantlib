from __future__ import annotations

import argparse
import logging
import sys

import tomlkit
import tomllib

from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import ConfigurationModel
from variantlib.configuration import VariantConfiguration
from variantlib.configuration import get_configuration_files
from variantlib.errors import ConfigurationError

logging.getLogger("variantlib").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def show(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="show",
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
        configuration = VariantConfiguration.get_config()
        config_files = get_configuration_files()

        for config_name in ConfigEnvironments:
            if (cfg_f := config_files[config_name]).exists():
                source_f = cfg_f
                break
        else:
            raise FileNotFoundError("No configuration file found.")

    else:
        source_f = get_configuration_files()[
            getattr(ConfigEnvironments, parsed_args.environment)
        ]

        if not source_f.exists():
            raise FileNotFoundError(
                f"The specified configuration [{parsed_args.environment}] file does "
                f"not exist: `{source_f}`."
            )

    with source_f.open("rb") as f:
        try:
            config = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigurationError from e

    configuration = ConfigurationModel.from_toml_config(**config)

    data = configuration.to_dict()
    doc = tomlkit.document()
    doc.add(tomlkit.comment(f"This file has been sourced from: `{source_f.resolve()}`"))
    doc.add(tomlkit.nl())  # Blank line after comment
    for idx, (key, items) in enumerate(data.items()):
        array = tomlkit.array().multiline(multiline=True)
        array.extend(items)
        doc[key] = array

        # Add a blank line if it's not the last item
        if idx < len(data) - 1:
            doc.add(tomlkit.nl())

    tomlkit.dump(doc, sys.stderr)
