from __future__ import annotations

import argparse
import logging
import sys

from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)


def analyze_platform(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="analyze_platform",
        description="Analyze the platform and return the variant hashes compatible",
    )
    _ = parser.parse_args(args)

    logger.info("Analyzing the platform ...\n")
    variant_cfgs = PluginLoader.get_supported_configs().values()

    # We have to flush the logger handlers to ensure that all logs are printed
    for handler in logger.handlers:
        handler.flush()

    for variant_cfg in variant_cfgs:
        for line in variant_cfg.pretty_print().splitlines():
            sys.stdout.write(f"{line}\n")
