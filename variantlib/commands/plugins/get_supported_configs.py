from __future__ import annotations

import argparse
import logging

from variantlib.commands.plugins._display_configs import display_configs
from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_supported_configs(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="get-supported-configs",
        description="CLI interface to get all supported configs on the machine",
    )

    parser.add_argument("-n", "--namespace", help="filter by namespace")
    parser.add_argument("-f", "--feature", help="filter by feature name")

    parsed_args = parser.parse_args(args)

    display_configs(
        list(PluginLoader.get_supported_configs().values()),
        namespace_filter=parsed_args.namespace,
        feature_filter=parsed_args.feature,
    )
