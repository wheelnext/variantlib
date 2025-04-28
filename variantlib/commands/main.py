# #!/usr/bin/env python3

from __future__ import annotations

import argparse
import logging
import sys

import variantlib
from variantlib import __package_name__

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def main() -> None:
    logger = logging.getLogger(__package_name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    registered_commands = entry_points(group=f"{__package_name__}.actions")

    parser = argparse.ArgumentParser(prog=__package_name__)
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s version: {variantlib.__version__}",
    )
    parser.add_argument(
        "command",
        choices=registered_commands.names,
    )
    parser.add_argument(
        "args",
        help=argparse.SUPPRESS,
        nargs=argparse.REMAINDER,
    )

    namespace = argparse.Namespace()
    parser.parse_args(namespace=namespace)

    main_fn = registered_commands[namespace.command].load()
    return main_fn(namespace.args)
