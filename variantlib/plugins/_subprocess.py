from __future__ import annotations

import argparse
import importlib
import json
import sys
from functools import reduce
from typing import TYPE_CHECKING

# TODO: inline these dependencies somehow
from variantlib.protocols import PluginType

if TYPE_CHECKING:
    from collections.abc import Generator


def load_plugins(plugin_apis: list[str]) -> Generator[PluginType]:
    for plugin_api in plugin_apis:
        # we expect variantlib to verify and normalize it
        import_name, attr_path = plugin_api.split(":")
        try:
            module = importlib.import_module(import_name)
            attr_chain = attr_path.split(".")
            plugin_callable = reduce(getattr, attr_chain, module)
        except Exception as exc:
            raise RuntimeError(
                f"Loading the plugin from {plugin_api!r} failed: {exc}"
            ) from exc

        if not callable(plugin_callable):
            raise TypeError(
                f"{plugin_api!r} points at a value that is not callable: "
                f"{plugin_callable!r}"
            )

        try:
            # Instantiate the plugin
            plugin_instance = plugin_callable()
        except Exception as exc:
            raise RuntimeError(
                f"Instantiating the plugin from {plugin_api!r} failed: {exc}"
            ) from exc

        required_attributes = PluginType.__abstractmethods__
        if missing_attributes := required_attributes.difference(dir(plugin_instance)):
            raise TypeError(
                f"Instantiating the plugin from {plugin_api!r} "
                "returned an object that does not meet the PluginType prototype: "
                f"{plugin_instance!r} (missing attributes: "
                f"{', '.join(sorted(missing_attributes))})"
            )

        yield plugin_instance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--plugin-api", action="append", help="Load specified plugin API"
    )
    parser.add_argument("command", choices={"namespaces"})
    args = parser.parse_args()
    plugins = dict(zip(args.plugin_api, load_plugins(args.plugin_api)))
    if args.command == "namespaces":
        json.dump(
            {plugin_api: plugin.namespace for plugin_api, plugin in plugins.items()},
            sys.stdout,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
