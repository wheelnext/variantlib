from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import tomlkit
from tomlkit.toml_file import TOMLFile

from variantlib import __package_name__
from variantlib.commands.config.setup_interfaces.console_ui import ConsoleUI
from variantlib.commands.config.setup_interfaces.urwid_ui import UrwidUI
from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import get_configuration_files
from variantlib.loader import PluginLoader
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.sorting import sort_variant_properties

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
----------------------------------------------------------------------------#
#                                INSTRUCTIONS                               #
#                                                                           #
# This command will set the variant configuration file for the requested    #
# environment. The configuration file is used to adjust the priority order  #
# of variants among the compatible variants on the system.                  #
#                                                                           #
-----------------------------------------------------------------------------

- Namespace Priorities [REQUIRED]:
    If more than one plugin is installed, this setting is mandatory to
    understand which variant namespace goes first.
    Example: `MPI` > `x86_64`
    ~ Meaning that `variantlib` will prioritize MPI support over special
      x86_64 optimizations. ~

-----------------------------------------------------------------------------

- Feature Priorities [OPTIONAL]:    - EXPERT USERS ONLY -
    For most users and usecases, this setting should stay empty & untouched.
    This allows to override the default ordering provided by the Variant
    Provider plugins.
    Example: `x86_64 :: aes` > `x86_64 :: sse3`
    ~ Meaning that `variantlib` will force prioritization of AES intrinsics
      over SSE3 support no matter what the variant provider plugin `x86_64` is
      recommending. ~

-----------------------------------------------------------------------------

- Property Priorities [OPTIONAL]:   - EXPERT USERS ONLY -
    For most users and usecases, this setting should stay empty & untouched.
    This allows to override the default ordering provided by the Variant
    Provider plugins.
    Example: `MPI :: Provider :: MPICH` > `MPI :: Provider :: OpenMPI`
    ~ Meaning that `variantlib` will force prioritization of MPICH use
      over OpenMPI use no matter what the variant provider plugin `MPI`
      is recommending. ~

"""


def setup(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{__package_name__} config setup",
        description="CLI interface to interactively set configuration up",
    )
    parser.add_argument(
        "-d",
        "--default",
        action="store_true",
        help="Fill the config with defaults non-interactively",
    )
    parser.add_argument(
        "-s",
        "--skip-instructions",
        action="store_true",
        help="Skip printing initial instructions",
    )
    parser.add_argument(
        "--ui",
        choices=("text", "urwid"),
        help="UI to use",
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

    if parsed_args.ui is None:
        parsed_args.ui = (
            "urwid" if sys.stdin.isatty() and sys.stdout.isatty() else "text"
        )
    ui = UrwidUI() if parsed_args.ui == "urwid" else ConsoleUI()

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
        with (Path(__file__).parent / "variants.dist.toml").open("rb") as f:
            toml_data = tomlkit.parse(f.read())
        path.parent.mkdir(parents=True, exist_ok=True)

    if not parsed_args.skip_instructions and not parsed_args.default:
        if not ui.display_text(INSTRUCTIONS):
            return

    if PluginLoader.plugins:
        known_namespaces = sorted(PluginLoader.namespaces)

        if parsed_args.default:
            toml_data["namespace_priorities"] = known_namespaces
            toml_data["feature_priorities"] = []
            toml_data["property_priorities"] = []
            sys.stdout.write(
                "Configuration reset to defaults, please edit the file to adjust "
                "priorities\n"
            )

        else:
            supported_configs = PluginLoader.get_supported_configs()

            ui.clear()
            namespace_priorities = ui.update_key(
                toml_data,
                "namespace_priorities",
                known_namespaces,
                known_values_required=True,
            )

            message = (
                "**Expert-Users Only**\n\n"
                "~ This setting should be left empty & untouched in most cases ~\n\n"
                "Do you wish to adjust variant-feature priorities?"
            )

            ui.clear()
            if ui.input_bool(message, default=False, height=9):
                known_features = [
                    VariantFeature(namespace, config.name).to_str()
                    for namespace, provider in sorted(
                        supported_configs.items(),
                        key=lambda kv: namespace_priorities.index(kv[0]),
                    )
                    for config in provider.configs
                ]
                ui.update_key(
                    toml_data,
                    "feature_priorities",
                    known_features,
                    known_values_required=False,
                )

            message = (
                "**Expert-Users Only**\n\n"
                "~ This setting should be left empty & untouched in most cases ~\n\n"
                "Do you wish to adjust variant-property priorities?"
            )

            ui.clear()
            if ui.input_bool(message, default=False, height=9):
                feature_priorities = [
                    VariantFeature.from_str(x)
                    for x in toml_data.get("feature_priorities", [])
                ]
                known_properties = [
                    vprop.to_str()
                    for vprop in sort_variant_properties(
                        [
                            VariantProperty(namespace, config.name, value)
                            for namespace, provider in supported_configs.items()
                            for config in provider.configs
                            for value in config.values
                        ],
                        namespace_priorities=namespace_priorities,
                        feature_priorities=feature_priorities,
                        property_priorities=None,
                    )
                ]
                ui.update_key(
                    toml_data,
                    "property_priorities",
                    known_properties,
                    known_values_required=False,
                )

        for key in (
            "namespace_priorities",
            "feature_priorities",
            "property_priorities",
        ):
            # Always use multiline output for readability.
            toml_data[key].multiline(multiline=True)

        ui.clear()
        sys.stderr.write(
            "Final configuration:\n"
            "\n"
            "```\n"
            # unwrap() converts to base Python type, effectively losing comments.
            f"{tomlkit.dumps(toml_data.unwrap())}"
            "```\n"
            "\n"
        )
        if parsed_args.ui != "urwid":
            if not ui.input_bool(
                "Do you want to save the configuration changes?",
                default=True,
            ):
                sys.stdout.write("Configuration changes discarded\n")
                return
    else:
        sys.stdout.write("No plugins found, empty configuration will be written\n")

    toml_file.write(toml_data)
    sys.stdout.write(f"Configuration file written to {path}\n")
