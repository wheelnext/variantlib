from __future__ import annotations

import argparse
import logging

from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def analyze_platform(args):
    parser = argparse.ArgumentParser(
        prog="analyze_platform",
        description="Analyze the platform and return the variant hashes compatible",
    )
    _ = parser.parse_args(args)

    logger.info("Analyzing the platform ... \n")
    variant_cfgs = PluginLoader.get_supported_configs().values()

    for variant_cfg in variant_cfgs:
        logger.info(variant_cfg.pretty_print())
        print()  # visual spacing  # noqa: T201

    logger.info(
        f"Total Variant Hashes: {2 ** sum(len(variant_cfg.configs) for variant_cfg in variant_cfgs):,}"  # noqa: G004, E501
    )
