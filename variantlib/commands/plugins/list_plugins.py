from __future__ import annotations

import argparse
import logging
import sys

from variantlib import __package_name__
from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)


def list_plugins(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} plugins list-plugins",
        description="CLI interface to list plugins",
    )

    parser.parse_args(args)

    for plugin_name in PluginLoader.plugins:
        sys.stdout.write(f"{plugin_name}\n")
