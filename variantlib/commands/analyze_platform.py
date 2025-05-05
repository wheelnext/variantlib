from __future__ import annotations

import argparse
import logging
import sys

from variantlib import __package_name__
from variantlib.commands.plugin_arguments import add_plugin_arguments
from variantlib.commands.plugin_arguments import parse_plugin_arguments

logger = logging.getLogger(__name__)


def analyze_platform(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} analyze-platform",
        description="Analyze the platform and return the variant hashes compatible",
    )

    add_plugin_arguments(parser)

    parsed_args = parser.parse_args(args)
    loader = parse_plugin_arguments(parsed_args)

    logger.info("Analyzing the platform ...\n")
    variant_cfgs = loader.get_supported_configs().values()

    # We have to flush the logger handlers to ensure that all logs are printed
    for handler in logger.handlers:
        handler.flush()

    for variant_cfg in variant_cfgs:
        for line in variant_cfg.pretty_print().splitlines():
            sys.stdout.write(f"{line}\n")
