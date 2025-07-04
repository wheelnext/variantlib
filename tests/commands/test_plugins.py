from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.commands.main import main

if TYPE_CHECKING:
    import pytest


def test_plugins_list(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "list"])
    assert (
        capsys.readouterr().out
        == """\
test_namespace
second_namespace
incompatible_namespace
"""
    )


def test_plugins_get_supported_configs(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-supported-configs"])
    assert (
        capsys.readouterr().out
        == """\
test_namespace :: name1 :: val1a
test_namespace :: name1 :: val1b
test_namespace :: name2 :: val2a
test_namespace :: name2 :: val2b
test_namespace :: name2 :: val2c
second_namespace :: name3 :: val3a
"""
    )


def test_plugins_get_supported_configs_filter_namespace(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-supported-configs", "-n", "second_namespace"])
    assert (
        capsys.readouterr().out
        == """\
second_namespace :: name3 :: val3a
"""
    )


def test_plugins_get_supported_configs_filter_feature(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-supported-configs", "-f", "name1"])
    assert (
        capsys.readouterr().out
        == """\
test_namespace :: name1 :: val1a
test_namespace :: name1 :: val1b
"""
    )


def test_plugins_validate_property(
    capsys: pytest.CaptureFixture[str], mocked_entry_points: None
) -> None:
    main(
        [
            "plugins",
            "validate-property",
            "test_namespace :: name1 :: val1a",
            "test_namespace :: name1::val1b",
            "test_namespace :: name2 :: val2a",
            "second_namespace:: name1:: val1a",
            "second_namespace::name3 :: val3a",
            "test_namespace  ::  name3    :: val3a",
            "unknown_namespace::foo::bar",
        ]
    )
    assert (
        capsys.readouterr().out
        == """\
test_namespace :: name1 :: val1a : valid
test_namespace :: name1 :: val1b : valid
test_namespace :: name2 :: val2a : valid
second_namespace :: name1 :: val1a : invalid
second_namespace :: name3 :: val3a : valid
test_namespace :: name3 :: val3a : invalid
unknown_namespace :: foo :: bar : no-plugin
"""
    )
