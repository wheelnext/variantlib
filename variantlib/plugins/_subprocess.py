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
from typing import Self

# The following imports are replaced with temporary paths by the plugin
# loader. We are using the original imports here to facilitate static
# checkers and easier debugging.
from variantlib.constants import VALIDATION_PROPERTY_REGEX
from variantlib.constants import VARIANTLIB_DYNAMIC_ANY_VALUE_MAGIC_VALUE
from variantlib.protocols import PluginDynamicType
from variantlib.protocols import PluginStaticType
from variantlib.protocols import VariantFeatureConfigType
from variantlib.validators.base import ValidationError
from variantlib.validators.base import validate_type

VariantFeatureName = str
VariantFeatureValue = str

if TYPE_CHECKING:
    from collections.abc import Generator


def load_plugins(
    plugin_apis: list[str],
) -> Generator[PluginStaticType | PluginDynamicType]:
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
        if callable(plugin_callable):
            try:
                # Instantiate the plugin
                plugin_instance = plugin_callable()
            except Exception as exc:
                raise RuntimeError(
                    f"Instantiating the plugin from {plugin_api!r} failed: {exc}"
                ) from exc
        else:
            plugin_instance = plugin_callable

        if isinstance(plugin_instance, PluginStaticType):
            plugin_type = PluginStaticType
        elif isinstance(plugin_instance, PluginDynamicType):
            plugin_type = PluginDynamicType
        else:
            raise TypeError(
                f"The plugin `{plugin_api!r}` does not meet any known interface."
            )

        required_attributes: set[str] = plugin_type.__abstractmethods__  # pyright: ignore[reportAttributeAccessIssue]
        if missing_attributes := required_attributes.difference(dir(plugin_instance)):
            raise TypeError(
                f"{plugin_api!r} does not meet the `{plugin_type.__name__}` prototype: "
                f"{plugin_instance!r} (missing attributes: "
                f"{', '.join(sorted(missing_attributes))})"
            )

        yield plugin_instance


def process_static_configs(
    configs: list[VariantFeatureConfigType],
    plugin_instance: PluginStaticType,
    method: str,
) -> list[dict[str, str | list[str]]]:
    try:
        validate_type(configs, list[VariantFeatureConfigType])
    except ValidationError as err:
        raise TypeError(
            f"Provider {plugin_instance.namespace}, {method}() "
            f"method returned incorrect type. {err}"
        ) from None

    return [{"name": vfeat.name, "values": vfeat.values} for vfeat in configs]


def process_dynamic_configs(
    configs: dict[VariantFeatureName, list[VariantFeatureValue]],
    plugin_instance: PluginDynamicType,
    method: str,
) -> list[dict[str, str | list[str]]]:
    try:
        validate_type(configs, dict[VariantFeatureName, list[VariantFeatureValue]])

    except ValidationError as err:
        raise TypeError(
            f"Provider {plugin_instance.namespace}, {method}() "
            f"method returned incorrect type. {err}"
        ) from None

    return [{"name": name, "values": values} for name, values in configs.items()]


@dataclass(frozen=True)
class VariantProperty:
    namespace: str
    feature: str
    value: str

    @classmethod
    def from_str(cls, input_str: str) -> Self:
        # Try matching the input string with the regex pattern
        match = VALIDATION_PROPERTY_REGEX.fullmatch(input_str.strip())

        if match is None:
            raise ValidationError(
                f"Invalid format: `{input_str}`, "
                "expected format: `<namespace> :: <feature> :: <value>`"
            )

        # Extract the namespace, feature, and value from the match groups
        namespace = match.group("namespace")
        feature = match.group("feature")
        value = match.group("value")

        # Return an instance of VariantProperty using the parsed values
        return cls(namespace=namespace, feature=feature, value=value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plugin-api",
        action="append",
        help="Load specified plugin API",
        required=True,
    )

    parser.add_argument(
        "--property",
        action="append",
        help="Variant Properties",
    )

    args = parser.parse_args()

    commands = json.load(sys.stdin)

    if args.property:
        vprops: list[VariantProperty] = [
            VariantProperty.from_str(val) for val in args.property
        ]
    else:
        vprops = []

    plugins = dict(zip(args.plugin_api, load_plugins(args.plugin_api)))
    namespace_map = {plugin.namespace: plugin for plugin in plugins.values()}

    retval: dict[str, Any] = {}
    for command, command_args in commands.items():
        if command == "namespaces":
            assert not command_args
            retval[command] = {
                plugin_api: plugin.namespace for plugin_api, plugin in plugins.items()
            }

        elif command == "get_all_configs":
            assert not command_args
            retval[command] = {  # pyright: ignore[reportArgumentType]
                plugin_api: (
                    process_static_configs(plugin.get_all_configs(), plugin, command)
                    if isinstance(plugin, PluginStaticType)
                    else process_dynamic_configs(
                        {
                            vfeat: [VARIANTLIB_DYNAMIC_ANY_VALUE_MAGIC_VALUE]
                            for vfeat in plugin.get_all_features()
                        },
                        plugin,
                        command,
                    )
                )
                for plugin_api, plugin in plugins.items()
            }

        elif command == "get_supported_configs":
            assert not command_args
            retval[command] = {  # pyright: ignore[reportArgumentType]
                plugin_api: (
                    process_static_configs(
                        plugin.get_supported_configs(), plugin, command
                    )
                    if isinstance(plugin, PluginStaticType)
                    else process_dynamic_configs(
                        plugin.filter_and_sort_properties(
                            vprops=vprops,  # pyright: ignore[reportArgumentType]
                            property_priorities=[],
                        ),
                        plugin,
                        command,
                    )
                )
                for plugin_api, plugin in plugins.items()
            }

        elif command == "get_build_setup":
            assert command_args
            assert "properties" in command_args
            ret_env: dict[str, list[str]] = {}
            for namespace, p_props in groupby(
                sorted(command_args["properties"], key=lambda prop: prop["namespace"]),
                lambda prop: prop["namespace"],
            ):
                plugin = namespace_map[namespace]
                if hasattr(plugin, "get_build_setup"):
                    plugin_env = plugin.get_build_setup(
                        [argparse.Namespace(**prop) for prop in p_props]  # pyright: ignore[reportArgumentType]
                    )

                    try:
                        validate_type(plugin_env, dict[str, list[str]])
                    except ValidationError as err:
                        raise TypeError(
                            f"Provider {namespace}, get_build_setup() "
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
