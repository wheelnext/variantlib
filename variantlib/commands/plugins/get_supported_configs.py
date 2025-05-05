from __future__ import annotations

import argparse
import logging
from typing import TYPE_CHECKING

from variantlib import __package_name__
from variantlib.commands.plugins._display_configs import display_configs

if TYPE_CHECKING:
    from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)


def get_supported_configs(args: list[str], plugin_loader: PluginLoader) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} plugins get-supported-configs",
        description="CLI interface to get all supported configs on the machine",
    )

    parser.add_argument("-n", "--namespace", help="filter by namespace")
    parser.add_argument("-f", "--feature", help="filter by feature name")

    parsed_args = parser.parse_args(args)

    display_configs(
        list(plugin_loader.get_supported_configs().values()),
        namespace_filter=parsed_args.namespace,
        feature_filter=parsed_args.feature,
    )
