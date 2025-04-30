from __future__ import annotations

import argparse
import logging

from variantlib import __package_name__
from variantlib.commands.plugins._display_configs import display_configs
from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)


def get_all_configs(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} plugins get-all-configs",
        description="CLI interface to get all valid configs",
    )

    parser.add_argument("-n", "--namespace", help="filter by namespace")
    parser.add_argument("-f", "--feature", help="filter by feature name")

    parsed_args = parser.parse_args(args)

    display_configs(
        list(PluginLoader.get_all_configs().values()),
        namespace_filter=parsed_args.namespace,
        feature_filter=parsed_args.feature,
        sort_vprops=True,
    )
