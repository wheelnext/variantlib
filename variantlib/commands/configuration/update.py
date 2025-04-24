from __future__ import annotations

import argparse
import importlib.resources
import logging
import sys
from itertools import chain
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import tomlkit
from tomlkit.toml_file import TOMLFile

from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import get_configuration_files
from variantlib.loader import PluginLoader

if TYPE_CHECKING:
    from types import ModuleType

    from tomlkit.toml_document import TOMLDocument

readline: ModuleType | None
try:
    import readline
except ImportError:
    # readline is optional
    readline = None


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def input_with_default(prompt: str, default: str) -> str:
    if readline is not None:

        def readline_hook() -> None:
            readline.insert_text(f"{default.strip()} ")
            readline.redisplay()

        readline.set_pre_input_hook(readline_hook)
        ret = input(f"{prompt}: ")
        readline.set_pre_input_hook()
    else:
        ret = input(f"{prompt} (current value: {default}): ")
    return ret


def index_string_to_values(
    index_map: dict[int, str], value_str: str
) -> list[str] | None:
    ret = []
    valid = True
    for index in value_str.split():
        try:
            new_value = index_map[int(index, 10)]
        except ValueError:  # noqa: PERF203
            sys.stderr.write(f"Value not a number: {index}\n")
            valid = False
        except KeyError:
            sys.stderr.write(f"Value out of range: {index}\n")
            valid = False
        else:
            if new_value in ret:
                sys.stderr.write(f"Duplicate value ignored: {index}\n")
            else:
                ret.append(new_value)
    return ret if valid else None


def update_namespaces(tomldoc: TOMLDocument) -> None:
    known_namespaces = sorted(PluginLoader.namespaces)
    value = tomldoc.setdefault("namespace_priorities", [])
    unknown_namespaces = sorted(set(value) - set(known_namespaces))

    index_map = {
        index + 1: namespace
        for index, namespace in enumerate(chain(known_namespaces, unknown_namespaces))
    }
    reverse_map = {
        namespace: index + 1
        for index, namespace in enumerate(chain(known_namespaces, unknown_namespaces))
    }

    sys.stderr.write(
        dedent("""\
        Namespace priorities
        ====================

        Please specify a space-separated list of numbers corresponding to the following
        namespaces, in preference order, starting with the most preferred namespace.
        All namespaces listed as "required" must be included.

        Required namespaces:\n""")
    )

    for index, namespace in index_map.items():
        # Switching to optional namespaces.
        if index == len(known_namespaces) + 1:
            sys.stderr.write("\nOptional namespaces:\n")
        sys.stderr.write(f"{index:3}. {namespace}\n")

    value_str = " ".join(f"{reverse_map[namespace]}" for namespace in value)
    while True:
        value_str = input_with_default("\nnamespace_priorities", value_str)
        value_list = index_string_to_values(index_map, value_str)
        if value_list is None:
            continue

        missing_namespaces = sorted(set(known_namespaces) - set(value_list))
        if missing_namespaces:
            sys.stderr.write(
                "Not all required namespaces specified.\n"
                "The following namespaces are missing:\n"
            )
            # Sort order is the same as index order.
            for namespace in sorted(missing_namespaces):
                sys.stderr.write(f"{reverse_map[namespace]:3}. {namespace}\n")
            continue

        break

    value.clear()
    value.extend(value_list)
    sys.stderr.write("\n")


def update(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="list-paths",
        description="CLI interface to interactively update configuration files",
    )
    parser.add_argument(
        "-d",
        "--default",
        action="store_true",
        help="Fill the config with defaults non-interactively",
    )

    excl_group = parser.add_mutually_exclusive_group()
    excl_group.add_argument(
        "-e",
        "--environment",
        choices=[x.name for x in ConfigEnvironments],
        help="environment name",
        default="USER",
    )
    excl_group.add_argument(
        "-p",
        "--path",
        type=Path,
        help="custom path to the config file",
    )

    parsed_args = parser.parse_args(args)

    # note: due to default= above, parsed_args.environment will never be None
    # however, argparse will still prevent the user from using `-p` and `-e`
    # simultaneously
    if parsed_args.path is not None:
        path = parsed_args.path
    else:
        path = get_configuration_files()[
            getattr(ConfigEnvironments, parsed_args.environment)
        ]

    toml_file = TOMLFile(path)
    try:
        toml_data = toml_file.read()
    except FileNotFoundError:
        toml_data = tomlkit.parse(
            importlib.resources.read_binary(__name__, "variants.dist.toml")
        )
        path.parent.mkdir(parents=True, exist_ok=True)

    if PluginLoader.plugins:
        if parsed_args.default:
            toml_data["namespace_priorities"] = sorted(PluginLoader.namespaces)
            toml_data["feature_priorities"] = []
            toml_data["property_priorities"] = []
            sys.stdout.write(
                "Configuration reset to defaults, please edit the file to adjust "
                "priorities\n"
            )
        else:
            update_namespaces(toml_data)

        for key in (
            "namespace_priorities",
            "feature_priorities",
            "property_priorities",
        ):
            # Always use multiline output for readability.
            toml_data[key].multiline(multiline=True)
    else:
        sys.stdout.write("No plugins found, empty configuration will be written\n")

    toml_file.write(toml_data)
    sys.stdout.write(f"Configuration file written to {path}\n")
