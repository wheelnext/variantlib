# #!/usr/bin/env python3

from __future__ import annotations

import sys

if sys.version_info >= (3, 10):
    from importlib.metadata import EntryPoint
    from importlib.metadata import entry_points
else:
    from importlib_metadata import EntryPoint
    from importlib_metadata import entry_points


def get_registered_commands(group: str) -> dict[str, EntryPoint]:
    """Collect entry points for the given group, preserving original names."""
    commands = {}
    for ep in entry_points().select(group=group):
        commands[ep.name] = ep
    return commands
