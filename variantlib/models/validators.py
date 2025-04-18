from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from types import GenericAlias
from typing import Any
from typing import Callable
from typing import Protocol
from typing import Union
from typing import get_args
from typing import get_origin

from variantlib.errors import ValidationError

logger = logging.getLogger(__name__)


def validate_matches_re(value: str, pattern: str) -> None:
    if not re.match(pattern, value):
        raise ValidationError(f"Value `{value}` must match regex {pattern}")


def validate_list_matches_re(values: list[str], pattern: str) -> None:
    for value in values:
        validate_matches_re(value, pattern)


def validate_list_min_len(values: list, min_length: int) -> None:
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
            raise ValidationError(f"Duplicate value found: '{_value}' in list.")

        seen.add(_value)


def validate_or(validators: list[Callable], value: Any) -> None:
    """
    Validate a value using a list of validators. If any validator raises an
    exception, the next one is tried. If all validators fail, the last exception
    is raised.
    """
    if not validators:
        raise ValidationError("No validators provided.")

    exceptions = []
    for validator in validators:
        try:
            validator(value)
            break

        except ValidationError as e:
            exceptions.append(e)
            continue

    else:
        if exceptions:
            for exc in exceptions:
                logger.exception(
                    "Validator %(name)s failed for value `%(value)s`",
                    {"name": validator.__name__, "value": value},
                    exc_info=exc,
                )
            raise exceptions[-1]


def validate_and(validators: list[Callable], value: Any) -> None:
    """
    Validate a value using a list of validators. If any validator raises an
    exception, the next one is tried. If all validators fail, the last exception
    is raised.
    """
    if not validators:
        raise ValueError("No validators provided.")

    try:
        for validator in validators:
            validator(value)

    except ValidationError:
        logger.exception(
            "Validator %(name)s failed for value `%(value)s`",
            {"name": validator.__name__, "value": value},
        )
        raise


def _validate_type(value: Any, expected_type: type) -> type | None:
    if isinstance(expected_type, GenericAlias):
        list_type = get_origin(expected_type)

        if not isinstance(value, list_type):
            return type(value)

        if list_type is dict:
            assert isinstance(value, dict)
            key_type, value_type = get_args(expected_type)
            incorrect_key_types = {_validate_type(key, key_type) for key in value}
            incorrect_key_types.discard(None)
            incorrect_value_types = {
                _validate_type(v, value_type) for v in value.values()
            }
            incorrect_value_types.discard(None)
            if incorrect_key_types or incorrect_value_types:
                key_ored = Union.__getitem__((key_type, *incorrect_key_types))
                value_ored = Union.__getitem__((value_type, *incorrect_value_types))
                return list_type[key_ored, value_ored]  # type: ignore[index]

        else:
            (item_type,) = get_args(expected_type)
            assert isinstance(value, Iterable)
            incorrect_types = {_validate_type(item, item_type) for item in value}
            incorrect_types.discard(None)
            if incorrect_types:
                ored = Union.__getitem__((item_type, *incorrect_types))
                return list_type[ored]  # type: ignore[index]

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
