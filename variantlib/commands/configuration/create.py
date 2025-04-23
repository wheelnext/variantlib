from __future__ import annotations

import argparse
import importlib.resources
import logging
import sys
from pathlib import Path

from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import get_configuration_files

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="list-paths",
        description="CLI interface to create configuration files from template",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite configuration file if one exists",
    )

    excl_group = parser.add_mutually_exclusive_group(required=True)
    excl_group.add_argument(
        "-e",
        "--environment",
        choices=[x.name for x in ConfigEnvironments],
        help="environment name",
    )
    excl_group.add_argument(
        "-p",
        "--path",
        type=Path,
        help="custom path to create at",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.environment is not None:
        path = get_configuration_files()[
            getattr(ConfigEnvironments, parsed_args.environment)
        ]
    else:
        path = parsed_args.path

    template = importlib.resources.read_binary(__name__, "variants.dist.toml")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = "w" if parsed_args.force else "x"
        with path.open(f"{mode}b") as f:
            f.write(template)
    except FileExistsError:
        parser.error(
            f"Configuration file at {path} exists, pass --force to overwrite it"
        )

    sys.stdout.write(f"Configuration file written to {path}\n")
