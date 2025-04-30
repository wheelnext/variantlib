from __future__ import annotations

import sys
from itertools import chain
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

    from tomlkit.toml_document import TOMLDocument

readline: ModuleType | None
try:
    import readline
except ImportError:
    # readline is optional
    readline = None


INSTRUCTIONS = {
    "namespace_priorities": """
Namespace priorities
====================

Please specify a space-separated list of numbers corresponding to the following
namespaces, in preference order, starting with the most preferred namespace.
All namespaces listed as "known" must be included.
""",
    "feature_priorities": """
Feature priorities
==================

Please specify a space-separated list of numbers corresponding to the following
features, in preference order, starting with the most preferred feature.
All feature priorities are optional.
""",
    "property_priorities": """
Property priorities
===================

Please specify a space-separated list of numbers corresponding to the following
properties, in preference order, starting with the most preferred properties.
All property priorities are optional.
""",
}


class ConsoleUI:
    def display_text(self, text: str) -> bool:
        sys.stderr.write(text)
        try:
            input("Press Enter to continue or Ctrl-C to abort...")
        except KeyboardInterrupt:
            sys.stderr.write("\nAborting.\n")
            return False
        return True

    def input_bool(self, prompt: str, default: bool) -> bool:
        full_prompt = f"{prompt} [{'Y/n' if default else 'y/N'}] "
        while True:
            val = input(full_prompt)
            if not val:
                return default
            if val.lower() in ("y", "yes"):
                return True
            if val.lower() in ("n", "no"):
                return False
            sys.stderr.write("Invalid reply!\n\n")

    def input_with_default(self, prompt: str, default: str) -> str:
        if readline is not None:

            def readline_hook() -> None:
                readline.insert_text(default.strip())
                if default.strip():
                    readline.insert_text(" ")
                readline.redisplay()

            readline.set_pre_input_hook(readline_hook)
            ret = input(f"{prompt}: ")
            readline.set_pre_input_hook()
        else:
            ret = input(f"{prompt} (current value: {default}): ")
        return ret

    def index_string_to_values(
        self, index_map: dict[int, str], value_str: str
    ) -> list[str] | None:
        ret = []
        valid = True
        for index in value_str.split():
            if not index.isdigit():
                sys.stderr.write(f"Value not a number: {index}\n")
                valid = False
                continue

            new_value = index_map.get(int(index, 10))
            if new_value is None:
                sys.stderr.write(f"Value out of range: {index}\n")
                valid = False
                continue

            if new_value in ret:
                sys.stderr.write(f"Duplicate value ignored: {index}\n")
            else:
                ret.append(new_value)
        return ret if valid else None

    def update_key(
        self,
        tomldoc: TOMLDocument,
        key: str,
        known_values: list[str],
        known_values_required: bool,
    ) -> list[str]:
        toml_values = tomldoc.setdefault(key, [])
        unknown_values = sorted(set(toml_values) - set(known_values))

        index_map = {
            index + 1: value
            for index, value in enumerate(chain(known_values, unknown_values))
        }
        reverse_map = {
            value: index + 1
            for index, value in enumerate(chain(known_values, unknown_values))
        }

        sys.stderr.write(INSTRUCTIONS[key])
        sys.stderr.write("\nKnown values:\n")

        for index, value in index_map.items():
            # Switching to optional values.
            if index == len(known_values) + 1:
                sys.stderr.write("\nUnrecognized values already in configuration:\n")
            sys.stderr.write(f"{index:3}. {value}\n")

        value_str = " ".join(f"{reverse_map[value]}" for value in toml_values)
        while True:
            value_str = self.input_with_default(f"\n{key}", value_str)
            new_values = self.index_string_to_values(index_map, value_str)
            if new_values is None:
                continue

            if known_values_required:
                missing_values = sorted(set(known_values) - set(new_values))
                if missing_values:
                    sys.stderr.write(
                        "Not all required values specified.\n"
                        "The following values are missing:\n"
                    )
                    # Sort order is the same as index order.
                    for value in sorted(missing_values):
                        sys.stderr.write(f"{reverse_map[value]:3}. {value}\n")
                    continue

            break

        toml_values.clear()
        toml_values.extend(new_values)
        sys.stderr.write("\n")
        return new_values
