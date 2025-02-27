# #!/usr/bin/env python3

import argparse
from importlib.metadata import entry_points

import variantlib


def main():
    registered_commands = entry_points(group="variantlib.actions")

    parser = argparse.ArgumentParser(prog="variantlib")
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

    args = argparse.Namespace()
    parser.parse_args(namespace=args)

    main_fn = registered_commands[args.command].load()
    return main_fn(args.args)