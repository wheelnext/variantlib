# #!/usr/bin/env python3

from __future__ import annotations

import argparse

from variantlib import __package_name__
from variantlib.commands.utils import get_registered_commands


def main(args: list[str]) -> None:
    registered_commands = get_registered_commands(group="variantlib.actions.config")

    parser = argparse.ArgumentParser(prog=f"{__package_name__} config")

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
