from __future__ import annotations

import re
from typing import Any


def validate_instance_of(value: Any, expected_type: type) -> None:
    if not isinstance(value, expected_type):
        raise TypeError(f"Expected {expected_type}, got {type(value)}")


def validate_list_of(data: list[Any], expected_type: type) -> None:
    for value in data:
        if not isinstance(value, expected_type):
            raise TypeError(f"Expected {expected_type}, got {type(value)}")


def validate_matches_re(value: str, pattern: str) -> None:
    if not re.match(pattern, value):
        raise ValueError(f"Value must match regex {pattern}")
