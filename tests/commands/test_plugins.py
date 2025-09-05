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


def test_plugins_get_all_configs(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--all"])
    assert (
        capsys.readouterr().out
        == """\
test_namespace :: name1 :: val1a
test_namespace :: name1 :: val1b
test_namespace :: name1 :: val1c
test_namespace :: name1 :: val1d
test_namespace :: name2 :: val2a
test_namespace :: name2 :: val2b
test_namespace :: name2 :: val2c
second_namespace :: name3 :: val3a
second_namespace :: name3 :: val3b
second_namespace :: name3 :: val3c
incompatible_namespace :: flag1 :: on
incompatible_namespace :: flag2 :: on
incompatible_namespace :: flag3 :: on
incompatible_namespace :: flag4 :: on
"""
    )


def test_plugins_get_all_configs_filter_namespace(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--all", "-n", "second_namespace"])
    assert (
        capsys.readouterr().out
        == """\
second_namespace :: name3 :: val3a
second_namespace :: name3 :: val3b
second_namespace :: name3 :: val3c
"""
    )


def test_plugins_get_all_configs_filter_feature(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--all", "-f", "name1"])
    assert (
        capsys.readouterr().out
        == """\
test_namespace :: name1 :: val1a
test_namespace :: name1 :: val1b
test_namespace :: name1 :: val1c
test_namespace :: name1 :: val1d
"""
    )


def test_plugins_get_supported_configs(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--supported"])
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
    main(["plugins", "get-configs", "--supported", "-n", "second_namespace"])
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
    main(["plugins", "get-configs", "--supported", "-f", "name1"])
    assert (
        capsys.readouterr().out
        == """\
test_namespace :: name1 :: val1a
test_namespace :: name1 :: val1b
"""
    )
