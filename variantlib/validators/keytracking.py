from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Any

from variantlib.errors import ValidationError
from variantlib.validators.base import _validate_type
from variantlib.validators.base import validate_list_matches_re
from variantlib.validators.base import validate_matches_re

if TYPE_CHECKING:
    import re


class KeyTrackingValidator:
    """Helper class for validating types in nested structure"""

    class RequiredKey: ...

    def __init__(self, top_key: str | None, top_data: dict[str, Any]) -> None:
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

    def matches_re(self, pattern: str | re.Pattern[str]) -> re.Match[str]:
        return validate_matches_re(self._data[-1], pattern, self._key)

    def list_matches_re(self, pattern: str | re.Pattern[str]) -> None:
        return validate_list_matches_re(self._data[-1], pattern, self._key)

    @contextmanager
    def get(
        self,
        key: str,
        expected_type: type,
        default: Any = RequiredKey,
        ignore_subkeys: bool = False,
    ) -> Any:
        # add to list of expected keys of current dict
        self._expected_keys[-1].add(key)

        # push the value to the stack
        self._keys.append(key)
        self._data.append(self._data[-1].get(key, default))

        if self._data[-1] is self.RequiredKey:
            raise ValidationError(f"{self._key}: required key not found")

        self._expected_keys.append(set())
        # validate only non-default type -- this makes optional keys easier
        # (since type validator can't handle optional types)
        if self._data[-1] is not default:
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
