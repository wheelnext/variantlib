from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from contextlib import contextmanager
from types import GenericAlias
from typing import Any
from typing import Callable
from typing import Protocol
from typing import Union
from typing import get_args
from typing import get_origin

from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement
from variantlib.errors import ValidationError

logger = logging.getLogger(__name__)


def validate_matches_re(
    value: str, pattern: str | re.Pattern, message_prefix: str | None = None
) -> re.Match:
    if (match := re.fullmatch(pattern, value)) is None:
        raise ValidationError(
            f"{message_prefix + ': ' if message_prefix is not None else ''}"
            f"Value `{value}` must match regex {pattern}"
        )
    return match


def validate_list_matches_re(
    values: list[str], pattern: str | re.Pattern, message_prefix: str | None = None
) -> None:
    for i, value in enumerate(values):
        validate_matches_re(
            value,
            pattern,
            message_prefix=f"{message_prefix}[{i}]"
            if message_prefix is not None
            else None,
        )


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
            raise ValidationError(f"Duplicate value found: `{_value}` in list.")

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
                return list_type[key_ored, value_ored]  # type: ignore[index]

        else:
            (item_type,) = get_args(expected_type)
            assert isinstance(value, Iterable)
            if item_type is not Any:
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


def validate_requirement_str(dependency_str: str) -> None:
    try:
        _ = Requirement(dependency_str)
    except (InvalidRequirement, ValueError) as e:
        raise ValidationError from e


class KeyTrackingValidator:
    """Helper class for validating types in nested structure"""

    def __init__(self, top_key: str | None, top_data: dict) -> None:
        self._keys = [top_key] if top_key else []
        self._data: list[Any] = [top_data]
        self._expected_keys: list[set[str]] = [set()]
        self.validate(top_data, dict[str, Any])

    @property
    def _key(self) -> str:
        return ".".join(self._keys)

    def validate(self, value: Any, expected_type: type) -> None:
        wrong_type = _validate_type(value, expected_type)
        if wrong_type is not None:
            raise ValidationError(
                f"{self._key}: expected {expected_type}, got {wrong_type}"
            )

    def matches_re(self, pattern: str | re.Pattern) -> re.Match:
        return validate_matches_re(self._data[-1], pattern, self._key)

    def list_matches_re(self, pattern: str | re.Pattern) -> None:
        return validate_list_matches_re(self._data[-1], pattern, self._key)

    @contextmanager
    def get(
        self,
        key: str,
        expected_type: type,
        default: Any = None,
        ignore_subkeys: bool = False,
    ) -> Any:
        # add to list of expected keys of current dict
        self._expected_keys[-1].add(key)

        # push the value to the stack
        self._keys.append(key)
        self._data.append(self._data[-1].get(key, default))

        if default is None and self._data[-1] is None:
            raise ValidationError(f"{self._key}: required key not found")

        self._expected_keys.append(set())
        self.validate(self._data[-1], expected_type)

        # return the value
        yield self._data[-1]

        # pop the value
        expected_keys = self._expected_keys.pop()
        last_data = self._data.pop()
        # if it was a dict, verify that we didn't get any unwelcome keys
        if isinstance(last_data, dict) and not ignore_subkeys:
            unexpected_keys = last_data.keys() - expected_keys
            if unexpected_keys:
                raise ValidationError(
                    f"{self._key}: unexpected subkeys: {unexpected_keys}; "
                    f"expected only: {expected_keys}"
                )
        self._keys.pop()
