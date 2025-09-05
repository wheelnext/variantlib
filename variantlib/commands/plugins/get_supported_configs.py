from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

from variantlib import __package_name__
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from variantlib.plugins.loader import BasePluginLoader

logger = logging.getLogger(__name__)


def get_supported_configs(args: list[str], plugin_loader: BasePluginLoader) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} plugins get-supported-configs",
        description="CLI interface to get all supported configs on the machine",
    )

    parser.add_argument("-n", "--namespace", help="filter by namespace")
    parser.add_argument("-f", "--feature", help="filter by feature name")

    parsed_args = parser.parse_args(args)

    for provider_cfg in plugin_loader.get_supported_configs().values():
        if parsed_args.namespace not in (provider_cfg.namespace, None):
            continue

        for feature in provider_cfg.configs:
            if parsed_args.feature not in (feature.name, None):
                continue

            for value in feature.values:
                vprop = VariantProperty(provider_cfg.namespace, feature.name, value)
                sys.stdout.write(f"{vprop.to_str()}\n")
