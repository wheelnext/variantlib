from __future__ import annotations

import argparse
import curses
import inspect
import logging
import sys
from textwrap import dedent

from variantlib.commands.configuration.utils import clear_console
from variantlib.commands.configuration.utils import get_user_preferences
from variantlib.commands.configuration.utils import read_toml_file
from variantlib.commands.configuration.utils import user_confirmation_prompt
from variantlib.commands.configuration.utils import write_toml_file
from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import get_configuration_files
from variantlib.constants import CONFIG_EXAMPLE_FILEPATH
from variantlib.loader import PluginLoader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_namespace_priorities(
    stdscr, instructions: str, user_options: dict[str, str]
) -> list[str]:
    ordered_options = []

    # Clear screen
    stdscr.clear()

    def get_user_choice(options):
        current_row = 0

        while True:
            stdscr.clear()

            stdscr.addstr(0, 0, instructions)

            line_offset = len(instructions.splitlines()) + 1
            for idx, (namespace, package_name) in enumerate(options.items()):
                option_str = (
                    f"Namespace: `{namespace + '`':20s} "
                    f"=> From Package: `{package_name}`"
                )
                if idx == current_row:
                    stdscr.addstr(
                        idx + line_offset, 0, f"> {option_str}", curses.A_REVERSE
                    )
                else:
                    stdscr.addstr(idx + line_offset, 0, f"  {option_str}")
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(options) - 1:
                current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                return current_row

    while user_options:
        choice_index = get_user_choice(user_options)
        value = list(user_options.keys())[choice_index]
        ordered_options.append(value)
        del user_options[value]

    stdscr.clear()

    return ordered_options


def set_configuration(args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="set",
        description="CLI interface to interactively set configuration files",
    )

    parser.add_argument(
        "environment",
        nargs="?",
        choices=[x.name for x in ConfigEnvironments],
        help="environment name to use",
        default="USER",
    )

    parser.add_argument(
        "-s",
        "--skip_instructions",
        action="store_true",
        help="print instructions on what these settings are and do",
    )

    parsed_args = parser.parse_args(args)

    comments, default_data = read_toml_file(CONFIG_EXAMPLE_FILEPATH)
    # Necessary to reset to empty as the example file contains dummy examples.
    for key in default_data:
        default_data[key] = []

    if not parsed_args.skip_instructions:
        sys.stdout.write(
            dedent("""
                -----------------------------------------------------------------------------------------------------------------
                #                                                  INSTRUCTIONS                                                 #
                #                                                                                                               #
                # This command will set the variant configuration file for the requested environment. The configuration file is #
                # used to adjust the priority order of variants among the compatible variants on the system.                    #
                #                                                                                                               #
                -----------------------------------------------------------------------------------------------------------------

                - Namespace Priorities [REQUIRED]:  If more than one plugin is installed, this setting is mandatory to
                                                    understand which variant namespace goes first.

                                                    Example: `MPI` > `SIMD`

                                                    ~ Meaning that `variantlib` will prioritize MPI support over special
                                                    SIMD instructions. ~

                -----------------------------------------------------------------------------------------------------------------

                - Feature Priorities [OPTIONAL]:    - EXPERT USERS ONLY -
                                                    For most users and usecases, this setting should stay empty & untouched.
                                                    This allows to override the default ordering provided by the Variant
                                                    Provider plugins.

                                                    Example: `SIMD :: AVX` > `SIMD :: SSE`

                                                    ~ Meaning that `variantlib` will force prioritization of AVX support over SSE
                                                    support no matter what the variant provider plugin `SIMD` is recommending. ~

                -----------------------------------------------------------------------------------------------------------------

                - Property Priorities [OPTIONAL]:   - EXPERT USERS ONLY -
                                                    For most users and usecases, this setting should stay empty & untouched.
                                                    This allows to override the default ordering provided by the Variant
                                                    Provider plugins.

                                                    Example: `SIMD :: AVX :: 2` > `SIMD :: AVX :: 512`

                                                    ~ Meaning that `variantlib` will force prioritization of AVX2 support over AVX512
                                                    support no matter what the variant provider plugin `SIMD` is recommending. ~
                \n\n""")  # noqa: E501
        )

    input("Press Enter to continue...")
    clear_console()

    if PluginLoader.plugins:
        # ======================== NAMESPACE PRIORITIES ======================== #

        instructions = dedent("""\
            Namespace Priorities
            ====================

            Please select the following variant namespaces, in preference order,
            starting with the most preferred namespace.\n""")

        known_namespaces = {
            namespace: inspect.getmodule(plugin_instance).__package__
            for namespace, plugin_instance in PluginLoader.plugins.items()
        }

        # Maximum 5 attempts for the user before exiting to avoid infinite loops.
        for _ in range(5):
            data = curses.wrapper(
                get_namespace_priorities, instructions, known_namespaces
            )
            clear_console()
            sys.stdout.write(
                "You elected to choose the following priority of namespaces:\n\n"
            )
            for idx, namespace in enumerate(data, 1):
                sys.stdout.write(f"{idx}. {namespace}\n")
            sys.stdout.write("\n")

            if user_confirmation_prompt(
                "Are you satisfied with the given order", default_is_true=True
            ):
                break
        else:
            raise RuntimeError("User was not able to select any namespace priorities.")
        default_data["namespace_priorities"] = data

        # ======================== FEATURE PRIORITIES ======================== #

        clear_console()
        if user_confirmation_prompt(
            "Do you wish to override the default variant feature order",
            default_is_true=False,
        ):
            instructions = dedent("""\
                Feature Priorities
                ==================

                Please select the following variant feature, in preference order,
                that you wish to prioritize above everything else.\n
                When you are done select EXIT.\n""")

            known_features = [
                "featureA",
                "featureB",
                "featureC",
                "featureD",
                "featureE",
                "featureF",
                "featureG",
                "featureH",
            ]

            default_data["feature_priorities"] = get_user_preferences(
                "feature priorities", instructions, known_features, is_optional=True
            )

        # ======================== PROPERTY PRIORITIES ======================== #

        clear_console()
        if user_confirmation_prompt(
            "Do you wish to override the default variant property order",
            default_is_true=False,
        ):
            instructions = dedent("""\
                Property Priorities
                ===================

                Please select the following variant properties, in preference order,
                that you wish to prioritize above everything else.\n
                When you are done select EXIT.\n""")

            known_features = [
                "propertyA",
                "propertyB",
                "propertyC",
                "propertyD",
                "propertyE",
                "propertyF",
            ]

            default_data["property_priorities"] = get_user_preferences(
                "property priorities", instructions, known_features, is_optional=True
            )

    else:
        sys.stdout.write("No plugins found, empty configuration will be written.\n")

    target_toml_filepath = get_configuration_files()[
        getattr(ConfigEnvironments, parsed_args.environment)
    ]

    write_toml_file(target_toml_filepath, comments, default_data)
