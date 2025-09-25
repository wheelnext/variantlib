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
test_namespace:
  name1: (single-value)
    val1a
    val1b
    val1c
    val1d
  name2: (single-value)
    val2a
    val2b
    val2c
second_namespace:
  name3: (single-value)
    val3a
    val3b
    val3c
incompatible_namespace:
  flag1: (single-value)
    on
  flag2: (single-value)
    on
  flag3: (single-value)
    on
  flag4: (single-value)
    on
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
second_namespace:
  name3: (single-value)
    val3a
    val3b
    val3c
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
test_namespace:
  name1: (single-value)
    val1a
    val1b
    val1c
    val1d
second_namespace:
incompatible_namespace:
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
test_namespace:
  name1: (single-value)
    val1a
    val1b
  name2: (single-value)
    val2a
    val2b
    val2c
second_namespace:
  name3: (single-value)
    val3a
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
second_namespace:
  name3: (single-value)
    val3a
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
test_namespace:
  name1: (single-value)
    val1a
    val1b
second_namespace:
"""
    )
