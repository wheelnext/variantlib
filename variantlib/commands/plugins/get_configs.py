from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
from typing import TYPE_CHECKING

from variantlib import __package_name__

if TYPE_CHECKING:
    from variantlib.plugins.loader import BasePluginLoader

logger = logging.getLogger(__name__)


def get_configs(args: list[str], plugin_loader: BasePluginLoader) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} plugins get-configs",
        description="CLI interface to get configs",
    )

    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument(
        "-a",
        "--all",
        action="store_const",
        dest="method",
        const="get_all_configs",
        help="Get all valid configs",
    )
    config_group.add_argument(
        "-s",
        "--supported",
        action="store_const",
        dest="method",
        const="get_supported_configs",
        help="Get supported configs",
    )
    parser.add_argument("-n", "--namespace", help="filter by namespace")
    parser.add_argument("-f", "--feature", help="filter by feature name")

    parsed_args = parser.parse_args(args)

    output: dict[str, list[dict[str, str | list[str]]]] = {}
    for provider_cfg in getattr(plugin_loader, parsed_args.method)().values():
        if parsed_args.namespace not in (provider_cfg.namespace, None):
            continue

        feature_list = output[provider_cfg.namespace] = []
        for feature in provider_cfg.configs:
            if parsed_args.feature not in (feature.name, None):
                continue

            feature_list.append(dataclasses.asdict(feature))

    json.dump(output, sys.stdout, indent=2)
