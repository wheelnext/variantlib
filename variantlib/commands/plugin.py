from __future__ import annotations

import argparse
import logging
import sys

from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def plugin(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="plugin",
        description="CLI interface to plugins",
    )
    subparsers = parser.add_subparsers(required=True, dest="command")
    list_cmd = subparsers.add_parser("list", help="list available plugins")
    list_cmd.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print distributions providing plugins",
    )

    parsed_args = parser.parse_args(args)
    if parsed_args.command == "list":
        for plugin_name in PluginLoader.plugins:
            if parsed_args.verbose:
                sys.stdout.write(
                    f"{plugin_name}\t{PluginLoader.distribution_names[plugin_name]}\n"
                )
            else:
                sys.stdout.write(f"{plugin_name}\n")
