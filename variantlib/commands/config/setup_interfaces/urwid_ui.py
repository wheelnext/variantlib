from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import urwid

if TYPE_CHECKING:
    from typing import Any

    from tomlkit.toml_document import TOMLDocument


COMMON_INSTRUCTION = (
    "Please order the {plural} according to their priority, most preferred {sing} "
    "first. Press [F7] or [Tab] to increase priority of the focused {sing}, "
    "[F8] to decrease its priority, [Enter] to toggle it. Only enabled {plural} "
    "will be included in the configuration."
)

INSTRUCTIONS = {
    "namespace_priorities": (
        f"{COMMON_INSTRUCTION.format(sing='namespace', plural='namespaces')}. "
        "The namespaces in bold are required and cannot be disabled."
    ),
    "feature_priorities": (
        f"{COMMON_INSTRUCTION.format(sing='feature', plural='features')}. "
        "All feature priorities are optional."
    ),
    "property_priorities": (
        f"{COMMON_INSTRUCTION.format(sing='property', plural='properties')}. "
        "All property priorities are optional."
    ),
}


class UrwidUI:
    palette = [
        ("button", "white", "dark cyan"),
        ("dialog", "white", "dark blue"),
        ("footer", "white", "dark blue"),
        ("footer_key", "yellow,bold", "dark blue"),
        ("list", "white", "dark cyan"),
        ("checkbox", "white", "dark cyan"),
        ("required_checkbox", "yellow,bold", "dark cyan"),
        ("highlight", "yellow,bold", "dark cyan"),
    ]

    def display_text(self, text: str) -> bool:
        def input_handler(key: str) -> None:
            if key == "enter":
                raise urwid.ExitMainLoop
            if key == " ":
                loop.process_input(["page down"])
            if key in ("q", "Q", "esc"):
                raise KeyboardInterrupt

        text_widget = urwid.Text(text)
        footer = urwid.AttrMap(
            urwid.Text(
                [
                    ("footer", "Press "),
                    ("footer_key", "Enter"),
                    ("footer", " to continue or "),
                    ("footer_key", "Q"),
                    ("footer", " to abort..."),
                ]
            ),
            "footer",
        )
        listbox = urwid.ListBox(urwid.SimpleListWalker([text_widget]))
        scrollable = urwid.ScrollBar(
            listbox, trough_char=urwid.ScrollBar.Symbols.LITE_SHADE
        )
        frame = urwid.Frame(scrollable, footer=footer)
        loop = urwid.MainLoop(frame, self.palette, unhandled_input=input_handler)
        try:
            loop.run()
        except KeyboardInterrupt:
            sys.stderr.write("\nAborting.\n")
            return False
        return True

    def input_bool(self, prompt: str, default: bool) -> bool:
        class State:
            retval: bool

            @classmethod
            def press(cls, val: bool) -> None:
                cls.retval = val
                raise urwid.ExitMainLoop

            @classmethod
            def input_handler(cls, key: str) -> None:
                if key in ("y", "Y"):
                    cls.retval = True
                    raise urwid.ExitMainLoop
                if key in ("esc", "n", "N"):
                    cls.retval = False
                    raise urwid.ExitMainLoop

        listbox = urwid.ListBox(
            urwid.SimpleListWalker(
                [
                    urwid.Text(prompt, urwid.CENTER),
                    urwid.Divider(),
                    urwid.GridFlow(
                        [
                            urwid.AttrMap(
                                urwid.Button(
                                    [("highlight", "Y"), ("button", "es")],
                                    lambda _: State.press(val=True),
                                ),
                                "button",
                            ),
                            urwid.AttrMap(
                                urwid.Button(
                                    [("highlight", "N"), ("button", "o")],
                                    lambda _: State.press(val=False),
                                ),
                                "button",
                            ),
                        ],
                        cell_width=10,
                        h_sep=3,
                        v_sep=1,
                        align=urwid.CENTER,
                        focus=(0 if default else 1),
                    ),
                ]
            )
        )
        frame = urwid.Filler(
            urwid.Padding(
                urwid.AttrMap(urwid.LineBox(listbox), "dialog"),
                align=urwid.CENTER,
                width=(urwid.RELATIVE, 50),
            ),
            height=6,
        )
        loop = urwid.MainLoop(frame, self.palette, unhandled_input=State.input_handler)
        loop.run()
        return State.retval

    def update_key(
        self,
        tomldoc: TOMLDocument,
        key: str,
        known_values: list[str],
        known_values_required: bool,
    ) -> None:
        toml_values = tomldoc.setdefault(key, [])
        toml_values_set = set(toml_values)
        all_values = toml_values + [
            value for value in known_values if value not in toml_values_set
        ]
        required_values_set = set(known_values) if known_values_required else set()

        class MovableCheckBox(urwid.CheckBox):
            def __init__(self, *args: Any, required: bool, **kwargs: Any):
                super().__init__(*args, **kwargs)
                self.mcb_required = required

            def toggle_state(self) -> None:
                if not self.mcb_required:
                    super().toggle_state()

            def keypress(self, size: tuple[int], key: str) -> str | None:
                if key in ("f7", "tab"):
                    old_pos = value_box.focus_position
                    if old_pos != 0:
                        item = value_box.body.pop(old_pos)
                        value_box.body.insert(old_pos - 1, item)
                        if old_pos != len(value_box.body) - 1:
                            value_box.focus_position -= 1
                    return None

                if key in ("f8",):
                    old_pos = value_box.focus_position
                    if old_pos != len(value_box.body) - 1:
                        item = value_box.body.pop(old_pos)
                        value_box.body.insert(old_pos + 1, item)
                        value_box.focus_position += 1
                    return None

                return super().keypress(size, key)

        def input_handler(key: str) -> None:
            if key in ("s", "S"):
                value_box.focus_position = len(value_box) - 2
            if key in ("esc", "a", "A"):
                value_box.focus_position = len(value_box) - 1

        def save_button(_: Any) -> None:
            raise urwid.ExitMainLoop

        def abort_button(_: Any) -> None:
            raise KeyboardInterrupt

        value_box = urwid.ListBox(
            urwid.SimpleListWalker(
                [
                    urwid.AttrMap(
                        MovableCheckBox(
                            value,
                            state=(
                                value in toml_values_set or value in required_values_set
                            ),
                            required=value in required_values_set,
                        ),
                        "required_checkbox"
                        if value in required_values_set
                        else "checkbox",
                    )
                    for value in all_values
                ]
                + [
                    urwid.Button([("highlight", "S"), ("list", "ave")], save_button),
                    urwid.Button([("highlight", "A"), ("list", "bort")], abort_button),
                ]
            )
        )
        listbox = urwid.Frame(
            urwid.ScrollBar(
                urwid.AttrMap(value_box, "list"),
                trough_char=urwid.ScrollBar.Symbols.LITE_SHADE,
            ),
            header=urwid.Text(INSTRUCTIONS[key]),
        )
        frame = urwid.Filler(
            urwid.Padding(
                urwid.AttrMap(urwid.LineBox(listbox, title=key), "dialog"),
                align=urwid.CENTER,
                width=(urwid.RELATIVE, 100),
                left=2,
                right=2,
            ),
            valign=urwid.MIDDLE,
            height=(urwid.RELATIVE, 100),
            top=2,
            bottom=2,
        )
        loop = urwid.MainLoop(frame, self.palette, unhandled_input=input_handler)
        loop.run()

        new_values = [
            item.base_widget.label
            for item in value_box.body
            if isinstance(item, urwid.AttrMap)
            and isinstance(item.base_widget, MovableCheckBox)
            and item.base_widget.get_state()
        ]

        toml_values.clear()
        toml_values.extend(new_values)
