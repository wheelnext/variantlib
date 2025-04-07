from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from types import GenericAlias
from typing import Any
from typing import Callable
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


def validate_list_all_unique(values: list[Any], key: None | Callable = None) -> None:
    """
    Validate that all elements in the list are unique.
    Raises a ValueError if duplicates are found.
    """
    seen = set()

    for value in values:
        if key is not None:
            value = key(value)  # noqa: PLW2901

        if value in seen:
            raise ValidationError(f"Duplicate value found: '{value}' in list.")

        seen.add(value)


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


def validate_type(value: Any, expected_type: type) -> None:
    """Validate that the value matches specified type"""

    if isinstance(expected_type, GenericAlias):
        list_type = get_origin(expected_type)
        if not isinstance(value, list_type):
            raise ValidationError(f"Expected {expected_type}, got {type(value)}")
        (item_type,) = get_args(expected_type)
        assert isinstance(value, Iterable)
        incorrect_types = {
            type(item) for item in value if not isinstance(item, item_type)
        }
        if incorrect_types:
            ored = item_type
            while incorrect_types:
                ored |= incorrect_types.pop()
            wrong_type = list_type[ored]  # type: ignore[index]
            raise ValidationError(f"Expected {expected_type}, got {wrong_type}")
    elif not isinstance(value, expected_type):
        raise ValidationError(f"Expected {expected_type}, got {type(value)}")
