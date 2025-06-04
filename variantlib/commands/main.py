# #!/usr/bin/env python3

from __future__ import annotations

import argparse
import logging

import variantlib
from variantlib import __package_name__
from variantlib.commands.utils import get_registered_commands


def main(args: list[str] | None = None) -> None:
    logger = logging.getLogger(__package_name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    registered_commands = get_registered_commands(group=f"{__package_name__}.actions")

    parser = argparse.ArgumentParser(prog=__package_name__)
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s version: {variantlib.__version__}",
    )
    parser.add_argument(
        "command",
        choices=sorted(registered_commands.keys()),
    )
    parser.add_argument(
        "args",
        help=argparse.SUPPRESS,
        nargs=argparse.REMAINDER,
    )

    namespace = argparse.Namespace()
    parser.parse_args(args=args, namespace=namespace)

    main_fn = registered_commands[namespace.command].load()
    main_fn(namespace.args)
