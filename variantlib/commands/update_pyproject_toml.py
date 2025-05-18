from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tomlkit.toml_file import TOMLFile

from variantlib import __package_name__
from variantlib.constants import PYPROJECT_TOML_DEFAULT_PRIO_KEY
from variantlib.constants import PYPROJECT_TOML_NAMESPACE_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_DATA_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import PYPROJECT_TOML_PROVIDER_REQUIRES_KEY
from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.plugins.loader import EntryPointPluginLoader
from variantlib.plugins.py_envs import ExternalNonIsolatedPythonEnv


def update_pyproject_toml(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} update-pyproject-toml",
        description="Update variant metadata in pyproject.toml",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default="./pyproject.toml",
        help="Path to TOML file to update (default: ./pyproject.toml)",
    )

    parser.add_argument(
        "-a",
        "--add",
        action="extend",
        nargs="+",
        default=[],
        help="Add provider sections for specified namespace(s)",
    )
    parser.add_argument(
        "-d",
        "--delete",
        action="extend",
        nargs="+",
        default=[],
        help="Remove provider sections for specified namespace(s)",
    )

    parsed_args = parser.parse_args(args)

    if not (parsed_args.add + parsed_args.delete):
        parser.error("No manipulations specified")

    toml_file = TOMLFile(parsed_args.file)
    try:
        toml_data = toml_file.read()
    except FileNotFoundError:
        parser.error(f"{str(parsed_args.file)!r} does not exist")

    # prepare all relevant tables
    variant_table = toml_data.setdefault(PYPROJECT_TOML_TOP_KEY, {})
    default_prio_table = variant_table.setdefault(PYPROJECT_TOML_DEFAULT_PRIO_KEY, {})
    namespace_prio_key = default_prio_table.setdefault(PYPROJECT_TOML_NAMESPACE_KEY, [])
    provider_table = variant_table.setdefault(PYPROJECT_TOML_PROVIDER_DATA_KEY, {})

    with (
        ExternalNonIsolatedPythonEnv() as py_ctx,
        EntryPointPluginLoader(python_ctx=py_ctx) as loader,
    ):
        for namespace in parsed_args.delete:
            while namespace in namespace_prio_key:
                namespace_prio_key.remove(namespace)
            if namespace in provider_table:
                del provider_table[namespace]

        for namespace in parsed_args.add:
            if namespace not in loader.namespaces:
                raise RuntimeError(
                    f"Plugin providing namespace `{namespace}` not installed."
                )

            if namespace not in namespace_prio_key:
                namespace_prio_key.append(namespace)

            namespace_table = provider_table.setdefault(namespace, {})
            namespace_table[PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY] = (
                loader.plugin_api_values[namespace]
            )
            default_requires = []
            if (dist := loader.plugin_provider_packages.get(namespace)) is not None:
                default_requires.append(f"{dist.name} >={dist.version}")
            namespace_table.setdefault(
                PYPROJECT_TOML_PROVIDER_REQUIRES_KEY, default_requires
            )

    toml_file.write(toml_data)
    sys.stdout.write(f"Wrote changes to {parsed_args.file}\n")
