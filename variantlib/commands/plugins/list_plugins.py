from __future__ import annotations

import argparse
import logging
import sys

from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)


def list_plugins(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="list-plugins",
        description="CLI interface to list plugins",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print distributions providing plugins",
    )

    parsed_args = parser.parse_args(args)

    for plugin_name in PluginLoader.plugins:
        if parsed_args.verbose:
            sys.stdout.write(
                f"{plugin_name}\t{PluginLoader.distribution_names[plugin_name]}\n"
            )
        else:
            sys.stdout.write(f"{plugin_name}\n")
