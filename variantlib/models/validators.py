from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable

from variantlib.errors import ValidationError

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


def validate_instance_of(value: Any, expected_type: type) -> None:
    if not isinstance(value, expected_type):
        raise ValidationError(f"Expected {expected_type}, got {type(value)}")


def validate_list_of(data: Iterable[Any], expected_type: type) -> None:
    for value in data:
        if not isinstance(value, expected_type):
            raise ValidationError(f"Expected {expected_type}, got {type(value)}")


def validate_matches_re(value: str, pattern: str) -> None:
    if not re.match(pattern, value):
        raise ValidationError(f"Value `{value}` must match regex {pattern}")


def validate_list_matches_re(values: list[str], pattern: str) -> None:
    for value in values:
        validate_matches_re(value, pattern)


def validate_list_min_len(value: list, min_length: int) -> None:
    if len(value) < min_length:
        raise ValidationError(
            f"List must have at least {min_length} elements, got {len(value)}"
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
