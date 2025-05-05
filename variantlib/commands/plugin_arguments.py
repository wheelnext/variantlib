from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from variantlib.loader import PluginLoader
from variantlib.pyproject_toml import VariantPyProjectToml

if TYPE_CHECKING:
    import argparse


def add_plugin_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p",
        "--plugin",
        action="append",
        default=[],
        help="Variant provider plugin api to load (can be specified multiple times)",
    )
    parser.add_argument(
        "--plugins-from-pyproject-toml",
        type=Path,
        action="append",
        default=[],
        help="Load all plugins specified in given pyproject.toml file "
        "(can be specified multiple times)",
    )


def parse_plugin_arguments(parsed_args: argparse.Namespace) -> PluginLoader:
    loader = PluginLoader()

    plugin_apis = set(parsed_args.plugin)
    for pyproject_toml_path in parsed_args.plugins_from_pyproject_toml:
        pyproject_toml = VariantPyProjectToml.from_path(pyproject_toml_path)
        plugin_apis.update(x.plugin_api for x in pyproject_toml.providers.values())

    for plugin_api in plugin_apis:
        loader.load_plugin(plugin_api)

    return loader
