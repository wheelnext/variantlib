from __future__ import annotations

import argparse
import logging
import sys

from variantlib.loader import PluginLoader
from variantlib.models.variant import VariantProperty

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def plugin(args: list[str]) -> None:  # noqa: C901
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

    get_all_configs_cmd = subparsers.add_parser(
        "get-all-configs", help="get all valid configs"
    )
    get_all_configs_cmd.add_argument("-n", "--namespace", help="filter by namespace")
    get_all_configs_cmd.add_argument("-f", "--feature", help="filter by feature name")

    get_supported_configs_cmd = subparsers.add_parser(
        "get-supported-configs", help="get supported configs"
    )
    get_supported_configs_cmd.add_argument(
        "-n", "--namespace", help="filter by namespace"
    )
    get_supported_configs_cmd.add_argument(
        "-f", "--feature", help="filter by feature name"
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
    elif parsed_args.command in ("get-all-configs", "get-supported-configs"):
        if parsed_args.command == "get-all-configs":
            configs = PluginLoader.get_all_configs()
        else:
            configs = PluginLoader.get_supported_configs()
        for provider in configs.values():
            if parsed_args.namespace not in (None, provider.namespace):
                continue
            for feature in provider.configs:
                if parsed_args.feature not in (None, feature.name):
                    continue
                for value in feature.values:
                    prop = VariantProperty(provider.namespace, feature.name, value)
                    sys.stdout.write(f"{prop.to_str()}\n")
