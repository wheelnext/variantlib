# -*- coding: utf-8 -*-

# =============================================================================== #
# IMPORTANT: this file is used in variantlib/plugins/_subprocess.py
#
# This file **MUST NOT** import any other `variantlib` module.
# Must be standalone.
# =============================================================================== #

from __future__ import annotations

import re
from collections.abc import Iterable
from types import GenericAlias
from typing import Any
from typing import Protocol
from typing import Union
from typing import get_args
from typing import get_origin


class ValidationError(ValueError):
    pass


def validate_matches_re(
    value: str, pattern: str | re.Pattern[str], message_prefix: str | None = None
) -> re.Match[str]:
    if (match := re.fullmatch(pattern, value)) is None:
        raise ValidationError(
            f"{message_prefix + ': ' if message_prefix is not None else ''}"
            f"Value `{value}` must match regex {pattern}"
        )
    return match


def validate_list_matches_re(
    values: list[str], pattern: str | re.Pattern[str], message_prefix: str | None = None
) -> None:
    for i, value in enumerate(values):
        validate_matches_re(
            value,
            pattern,
            message_prefix=f"{message_prefix}[{i}]"
            if message_prefix is not None
            else None,
        )


def validate_list_min_len(values: list[Any], min_length: int) -> None:
    if len(values) < min_length:
        raise ValidationError(
            f"List must have at least {min_length} elements, got {len(values)}"
        )


def validate_list_all_unique(values: list[Any], keys: list[str] | None = None) -> None:
    """
    Validate that all elements in the list are unique.
    Raises a ValueError if duplicates are found.
    """
    seen = set()

    for value in values:
        _value = value

        if keys is not None:
            _value = tuple([getattr(value, key) for key in keys])
            if len(_value) == 1:
                _value = _value[0]

        if _value in seen:
            raise ValidationError(f"Duplicate value found: `{_value}` in list.")

        seen.add(_value)


def _validate_type(value: Any, expected_type: type) -> type | None:
    if isinstance(expected_type, GenericAlias):
        list_type = get_origin(expected_type)

        if not isinstance(value, list_type):
            return type(value)

        if list_type is dict:
            assert isinstance(value, dict)
            key_type, value_type = get_args(expected_type)
            if key_type is not Any:
                incorrect_key_types = {_validate_type(key, key_type) for key in value}
                incorrect_key_types.discard(None)
            else:
                incorrect_key_types = set()
            if value_type is not Any:
                incorrect_value_types = {
                    _validate_type(v, value_type) for v in value.values()
                }
                incorrect_value_types.discard(None)
            else:
                incorrect_value_types = set()
            if incorrect_key_types or incorrect_value_types:
                key_ored = Union.__getitem__((key_type, *incorrect_key_types))
                value_ored = Union.__getitem__((value_type, *incorrect_value_types))
                return list_type[key_ored, value_ored]  # type: ignore[no-any-return,index]

        else:
            (item_type,) = get_args(expected_type)
            assert isinstance(value, Iterable)
            if item_type is not Any:
                incorrect_types = {_validate_type(item, item_type) for item in value}
                incorrect_types.discard(None)
                if incorrect_types:
                    ored = Union.__getitem__((item_type, *incorrect_types))
                    return list_type[ored]  # type: ignore[no-any-return,index]

    # Protocols and Iterable must enable subclassing to pass
    elif issubclass(expected_type, (Protocol, Iterable)):  # type: ignore[arg-type]
        if not isinstance(value, expected_type):
            return type(value)

    # Do not use isinstance here - we want to reject subclasses
    elif type(value) is not expected_type:
        return type(value)

    return None


def validate_type(value: Any, expected_type: type) -> None:
    """Validate that the value matches specified type"""

    wrong_type = _validate_type(value, expected_type)
    if wrong_type is not None:
        raise ValidationError(f"Expected {expected_type}, got {wrong_type}")
