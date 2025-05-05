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
        help="Plugin entry point to load (can be specified multiple times)",
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

    entry_points = set(parsed_args.plugin)
    for pyproject_toml_path in parsed_args.plugins_from_pyproject_toml:
        pyproject_toml = VariantPyProjectToml.from_path(pyproject_toml_path)
        entry_points.update(x.entry_point for x in pyproject_toml.providers.values())

    for entry_point in entry_points:
        loader.load_plugin(entry_point)

    return loader
