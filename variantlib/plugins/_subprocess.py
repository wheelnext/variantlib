from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass
from functools import reduce
from itertools import groupby
from typing import TYPE_CHECKING
from typing import Any

# The following imports are replaced with temporary paths by the plugin
# loader. We are using the original imports here to facilitate static
# checkers and easier debugging.
from variantlib.protocols import PluginType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.validators.base import ValidationError
from variantlib.validators.base import validate_type

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass(frozen=True)
class VariantProperty:
    namespace: str
    feature: str
    value: str


def load_plugins(plugin_apis: list[str]) -> Generator[PluginType]:
    for plugin_api in plugin_apis:
        # we expect variantlib to verify and normalize it
        import_name, _, attr_path = plugin_api.partition(":")
        try:
            module = importlib.import_module(import_name)
            attr_chain = attr_path.split(".") if attr_path else []
            plugin_callable = reduce(getattr, attr_chain, module)
        except Exception as exc:
            raise RuntimeError(
                f"Loading the plugin from {plugin_api!r} failed: {exc}"
            ) from exc

        # plugin-api can either be a callable (e.g. a class to instantiate
        # or a function to call) or a ready object
        plugin_instance: PluginType
        if callable(plugin_callable):
            try:
                # Instantiate the plugin
                plugin_instance = plugin_callable()
            except Exception as exc:
                raise RuntimeError(
                    f"Instantiating the plugin from {plugin_api!r} failed: {exc}"
                ) from exc
        else:
            plugin_instance = plugin_callable  # pyright: ignore[reportAssignmentType]

        # We cannot use isinstance() here since some of the PluginType methods
        # are optional. Instead, we use @abstractmethod decorator to naturally
        # annotate required methods, and the remaining methods are optional.
        required_attributes = PluginType.__abstractmethods__  # pyright: ignore[reportAttributeAccessIssue]
        if missing_attributes := required_attributes.difference(dir(plugin_instance)):
            raise TypeError(
                f"{plugin_api!r} does not meet the PluginType prototype: "
                f"{plugin_instance!r} (missing attributes: "
                f"{', '.join(sorted(missing_attributes))})"
            )

        yield plugin_instance


def process_configs(
    configs: list[VariantFeatureConfigType], plugin_instance: PluginType, method: str
) -> list[dict[str, str | list[str]]]:
    try:
        validate_type(configs, list[VariantFeatureConfigType])
    except ValidationError as err:
        raise TypeError(
            f"Provider {plugin_instance.namespace}, {method}() "
            f"method returned incorrect type. {err}"
        ) from None

    return [{"name": vfeat.name, "values": vfeat.values} for vfeat in configs]


def group_properties_by_plugin(
    properties: list[dict[str, str]], namespace_map: dict[str, PluginType]
) -> Generator[tuple[PluginType, frozenset[VariantProperty]]]:
    for namespace, p_props in groupby(
        sorted(properties, key=lambda prop: prop["namespace"]),
        lambda prop: prop["namespace"],
    ):
        plugin = namespace_map[namespace]
        yield (plugin, frozenset(VariantProperty(**prop) for prop in p_props))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plugin-api",
        action="append",
        help="Load specified plugin API",
        required=True,
    )
    args = parser.parse_args()
    commands = json.load(sys.stdin)
    plugins = dict(zip(args.plugin_api, load_plugins(args.plugin_api)))
    namespace_map = {plugin.namespace: plugin for plugin in plugins.values()}

    retval: dict[str, Any] = {}
    for command, command_args in commands.items():
        if command == "namespaces":
            assert not command_args
            retval[command] = {
                plugin_api: plugin.namespace for plugin_api, plugin in plugins.items()
            }
        elif command in ("get_all_configs", "get_supported_configs"):
            assert command_args
            assert "properties" in command_args
            retval[command] = {  # pyright: ignore[reportArgumentType]
                plugin_api: process_configs(
                    getattr(plugin, command)(
                        frozenset(
                            VariantProperty(**prop)
                            for prop in command_args["properties"]
                            if prop["namespace"] == plugin.namespace
                        )
                        if plugin.dynamic
                        else None
                    ),
                    plugin,
                    command,
                )
                for plugin_api, plugin in plugins.items()
            }
        elif command == "get_build_setup":
            assert command_args
            assert "properties" in command_args
            ret_env: dict[str, list[str]] = {}
            for plugin, p_props in group_properties_by_plugin(
                command_args["properties"], namespace_map
            ):
                if hasattr(plugin, "get_build_setup"):
                    plugin_env = plugin.get_build_setup(p_props)

                    try:
                        validate_type(plugin_env, dict[str, list[str]])
                    except ValidationError as err:
                        raise TypeError(
                            f"Provider {plugin.namespace}, get_build_setup() "
                            f"method returned incorrect type. {err}"
                        ) from None
                else:
                    plugin_env = {}

                for k, v in plugin_env.items():
                    ret_env.setdefault(k, []).extend(v)
            retval = {command: ret_env}
        else:
            raise ValueError(f"Invalid command: {command}")

    json.dump(retval, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
