from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.loader import PluginLoader

if TYPE_CHECKING:
    import argparse


def add_plugin_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p",
        "--plugin",
        action="append",
        required=True,
        help="Plugin entry point to load (can be specified multiple times)",
    )


def parse_plugin_arguments(parsed_args: argparse.Namespace) -> type[PluginLoader]:
    for entry_point in parsed_args.plugin:
        PluginLoader.load_plugin(entry_point)

    return PluginLoader
