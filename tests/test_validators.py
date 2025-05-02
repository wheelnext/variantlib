import json
import pathlib
import re
from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import Union
from typing import runtime_checkable

import pytest

from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.validators import ValidationError
from variantlib.validators import validate_type
from variantlib.validators import validate_variants_json


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
        ([1, "foo", True], list[Any]),
        ({1, "foo"}, set[Any]),
        ({"a": 1, "b": "foo", "c": True}, dict[str, Any]),
        ({"a": 1, 1: "foo", False: True}, dict[Any, Any]),
        ({"a": 1, 1: 2, False: 3}, dict[Any, int]),
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
        ({"a": 1, 1: "foo", "c": True}, dict[str, Any], dict[Union[str, int], Any]),
        ({"a": 1, 1: "foo", False: 3}, dict[Any, int], dict[Any, Union[int, str]]),
    ],
)
def test_validate_type_bad(value: Any, expected: type, have: type):
    with pytest.raises(
        ValidationError, match=re.escape(f"Expected {expected}, got {have}")
    ):
        validate_type(value, expected)


def test_validate_variants_json():
    json_file = pathlib.Path("tests/artifacts/variants.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    # Read the Variants JSON file
    with json_file.open() as f:
        data = json.load(f)

    validate_variants_json(data)

    for vhash, vdata in data["variants"].items():
        assert isinstance(vhash, str)
        assert isinstance(vdata, dict)

        vprops = []

        for namespace, feature_data in vdata.items():
            assert isinstance(namespace, str)
            assert isinstance(feature_data, dict)

            for feature_name, feature_value in feature_data.items():
                assert isinstance(feature_name, str)
                assert isinstance(feature_value, str)
                vprops.append(VariantProperty(namespace, feature_name, feature_value))

        assert VariantDescription(vprops).hexdigest == vhash, (
            f"Found `{VariantDescription(vprops).hexdigest}` - Expected {vhash}"
        )


def test_validate_variants_json_empty():
    validate_variants_json({"variants": {}})


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"variants": ["abcd1234"]},
        {"variants": {"abcd12345": {}}},
        {"variants": {"abcd1234": {}}},
        {"variants": {"abcd1234": ["namespace"]}},
        {"variants": {"abcd1234": {"namespace": [{"feature": "value"}]}}},
        {"variants": {"abcd1234": {"namespace": {}}}},
        {"variants": {"abcd1234": {"namespace": {"feature": 1}}}},
        {"variants": {"abcd1234": {"namespace": {"feature": "variant@python"}}}},
        {"variants": {"abcd1234": {"namespace": {"feature@variant": "python"}}}},
        {"variants": {"abcd1234": {"namesp@ce": {"feature": "value"}}}},
    ],
)
def test_validate_variants_json_incorrect_vhash(data: dict):
    with pytest.raises(ValidationError):
        validate_variants_json(data)
