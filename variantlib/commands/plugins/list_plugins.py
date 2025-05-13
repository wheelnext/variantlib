from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

from variantlib import __package_name__

if TYPE_CHECKING:
    from variantlib.plugins.loader import BasePluginLoader

logger = logging.getLogger(__name__)


def list_plugins(args: list[str], plugin_loader: BasePluginLoader) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} plugins list-plugins",
        description="CLI interface to list plugins",
    )

    parser.parse_args(args)

    for plugin_name in plugin_loader.plugins:
        sys.stdout.write(f"{plugin_name}\n")
