# #!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys

from variantlib import __package_name__
from variantlib.commands.plugin_arguments import add_plugin_arguments
from variantlib.commands.plugin_arguments import parse_plugin_arguments
from variantlib.plugins.loader import CLIPluginLoader
from variantlib.plugins.py_envs import ExternalNonIsolatedPythonEnv

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def main(args: list[str]) -> None:
    registered_commands = entry_points(group="variantlib.actions.plugins")

    parser = argparse.ArgumentParser(prog=f"{__package_name__} plugins")

    add_plugin_arguments(parser)

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
    parsed_args = parser.parse_args(args=args, namespace=namespace)
    plugin_apis = parse_plugin_arguments(parsed_args)

    with ExternalNonIsolatedPythonEnv() as py_ctx:  # noqa: SIM117
        with CLIPluginLoader(plugin_apis=plugin_apis, python_ctx=py_ctx) as loader:
            main_fn = registered_commands[namespace.command].load()
            return main_fn(namespace.args, plugin_loader=loader)
