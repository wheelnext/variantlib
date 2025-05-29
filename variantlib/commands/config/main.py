# #!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys

from variantlib import __package_name__

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def main(args: list[str]) -> None:
    registered_commands = entry_points(group="variantlib.actions.config")

    parser = argparse.ArgumentParser(prog=f"{__package_name__} config")

    parser.add_argument(
        "command",
        choices=sorted(registered_commands.names),
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
