from __future__ import annotations

from dataclasses import dataclass

import pytest

from variantlib.constants import VALIDATION_WHEEL_NAME_REGEX


@dataclass
class WheelNameTuple:
    base_wheel_name: str
    namever: str
    name: str
    ver: str
    build: str | None
    pyver: str
    abi: str
    plat: str
    variant_hash: str | None


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (
            # no build tag and no variant hash
            "foo-1.2.3-py3-none-any.whl",
            WheelNameTuple(
                base_wheel_name="foo-1.2.3-py3-none-any",
                namever="foo-1.2.3",
                name="foo",
                ver="1.2.3",
                build=None,
                pyver="py3",
                abi="none",
                plat="any",
                variant_hash=None,
            ),
        ),
        (
            # build tag and no variant hash
            "foo-1.2.3-5foo-py3-none-any.whl",
            WheelNameTuple(
                base_wheel_name="foo-1.2.3-5foo-py3-none-any",
                namever="foo-1.2.3",
                name="foo",
                ver="1.2.3",
                build="5foo",
                pyver="py3",
                abi="none",
                plat="any",
                variant_hash=None,
            ),
        ),
        (
            # no build tag and variant hash
            "foo-1.2.3-py3-none-any-12345678.whl",
            WheelNameTuple(
                base_wheel_name="foo-1.2.3-py3-none-any",
                namever="foo-1.2.3",
                name="foo",
                ver="1.2.3",
                build=None,
                pyver="py3",
                abi="none",
                plat="any",
                variant_hash="12345678",
            ),
        ),
        (
            # build tag and variant hash
            "foo-1.2.3-5foo-py3-none-any-12345678.whl",
            WheelNameTuple(
                base_wheel_name="foo-1.2.3-5foo-py3-none-any",
                namever="foo-1.2.3",
                name="foo",
                ver="1.2.3",
                build="5foo",
                pyver="py3",
                abi="none",
                plat="any",
                variant_hash="12345678",
            ),
        ),
        (
            # pytag that looks like build tag
            "foo-1.2.3-3-none-any.whl",
            WheelNameTuple(
                base_wheel_name="foo-1.2.3-3-none-any",
                namever="foo-1.2.3",
                name="foo",
                ver="1.2.3",
                build=None,
                pyver="3",
                abi="none",
                plat="any",
                variant_hash=None,
            ),
        ),
        (
            # pytag that looks like build tag and variant hash
            # (this is a known shortcoming)
            "foo-1.2.3-3-none-any-12345678.whl",
            WheelNameTuple(
                base_wheel_name="foo-1.2.3-3-none-any-12345678",
                namever="foo-1.2.3",
                name="foo",
                ver="1.2.3",
                build="3",
                pyver="none",
                abi="any",
                plat="12345678",
                variant_hash=None,
            ),
        ),
    ],
)
def test_wheel_name_regex(name: str, expected: WheelNameTuple) -> None:
    assert (match := VALIDATION_WHEEL_NAME_REGEX.fullmatch(name)) is not None
    assert WheelNameTuple(*match.groups()) == expected
