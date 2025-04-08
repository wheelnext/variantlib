import re
from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import Union
from typing import runtime_checkable

import pytest

from variantlib.models.validators import ValidationError
from variantlib.models.validators import validate_type


@runtime_checkable
class MyProtocol(Protocol):
    @property
    def a(self) -> int: ...

    @property
    def b(self) -> str: ...


@dataclass
class HalfClass:
    a: int


@dataclass
class MyClass(HalfClass):
    b: str


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, type(None)),
        (False, bool),
        (11, int),
        (4.5, float),
        (b"foo", bytes),
        ("foo", str),
        ([1, 2, 3], list[int]),
        ([], list[int]),
        ({1, 2, 3}, set[int]),
        (set(), set[int]),
        (MyClass(1, "2"), MyProtocol),
        ([[1], [2, 3], [4, 5]], list[list[int]]),
        ([[[1], [2, 3], [4, 5]]], list[list[list[int]]]),
        ({"a": 1, "b": 2}, dict[str, int]),
        ({"a": [1, 2, 3], "b": [4]}, dict[str, list[int]]),
    ],
)
def test_validate_type_good(value: Any, expected: type):
    validate_type(value, expected)


@pytest.mark.parametrize(
    ("value", "expected", "have"),
    [
        (None, bool, type(None)),
        (False, str, bool),
        (11, float, int),
        (4.5, int, float),
        (b"foo", str, bytes),
        ("foo", bytes, str),
        ([1, 2, 3], set[int], list),
        ([1, 2, 3], list[str], list[Union[str, int]]),
        (["1", 2, "3"], list[str], list[Union[str, int]]),
        ({1, 2, 3}, list[int], set),
        ({1, 2, 3}, set[str], set[Union[str, int]]),
        ({"1", 2, "3"}, set[str], set[Union[str, int]]),
        (11, MyProtocol, int),
        (object(), MyProtocol, object),
        ({"a": 1, "b": "2"}, MyProtocol, dict),
        (HalfClass(1), MyProtocol, HalfClass),
        (
            [[1], ["2", 3], ["4", "5"]],
            list[list[int]],
            list[Union[list[int], list[Union[int, str]]]],
        ),
        ([[1], {2, 3}, [4, 5]], list[list[int]], list[Union[list[int], set]]),
        ([1, 2, 3], list[list[int]], list[Union[list[int], int]]),
        (
            [[[1], [2, "3"], ["4", 5]]],
            list[list[list[int]]],
            list[Union[list[list[int]], list[Union[list[int], list[Union[int, str]]]]]],
        ),
        ({"a": "1", "b": 2}, dict[str, int], dict[str, Union[int, str]]),
        (
            {"a": [1, "2", 3], "b": ["4"]},
            dict[str, list[int]],
            dict[str, Union[list[int], list[Union[int, str]]]],
        ),
        (
            {"a": [1, 2, 3], "b": 4},
            dict[str, list[int]],
            dict[str, Union[list[int], int]],
        ),
    ],
)
def test_validate_type_bad(value: Any, expected: type, have: type):
    with pytest.raises(
        ValidationError, match=re.escape(f"Expected {expected}, got {have}")
    ):
        validate_type(value, expected)
