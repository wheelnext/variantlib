from __future__ import annotations

from typing import TYPE_CHECKING

from inline_snapshot import snapshot
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
    assert capsys.readouterr().out == snapshot("""\
test_namespace:
  - name: name1
    multi_value: false
    values:
    - val1a
    - val1b
    - val1c
    - val1d
  - name: name2
    multi_value: true
    values:
    - val2a
    - val2b
    - val2c
second_namespace:
  - name: name3
    multi_value: false
    values:
    - val3a
    - val3b
    - val3c
incompatible_namespace:
  - name: flag1
    multi_value: false
    values:
    - on
  - name: flag2
    multi_value: false
    values:
    - on
  - name: flag3
    multi_value: false
    values:
    - on
  - name: flag4
    multi_value: false
    values:
    - on
""")


def test_plugins_get_all_configs_filter_namespace(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--all", "-n", "second_namespace"])
    assert capsys.readouterr().out == snapshot("""\
second_namespace:
  - name: name3
    multi_value: false
    values:
    - val3a
    - val3b
    - val3c
""")


def test_plugins_get_all_configs_filter_feature(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--all", "-f", "name1"])
    assert capsys.readouterr().out == snapshot("""\
test_namespace:
  - name: name1
    multi_value: false
    values:
    - val1a
    - val1b
    - val1c
    - val1d
second_namespace: []
incompatible_namespace: []
""")


def test_plugins_get_supported_configs(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--supported"])
    assert capsys.readouterr().out == snapshot("""\
test_namespace:
  - name: name1
    multi_value: false
    values:
    - val1a
    - val1b
  - name: name2
    multi_value: true
    values:
    - val2a
    - val2b
    - val2c
second_namespace:
  - name: name3
    multi_value: false
    values:
    - val3a
""")


def test_plugins_get_supported_configs_filter_namespace(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--supported", "-n", "second_namespace"])
    assert capsys.readouterr().out == snapshot("""\
second_namespace:
  - name: name3
    multi_value: false
    values:
    - val3a
""")


def test_plugins_get_supported_configs_filter_feature(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--supported", "-f", "name1"])
    assert capsys.readouterr().out == snapshot("""\
test_namespace:
  - name: name1
    multi_value: false
    values:
    - val1a
    - val1b
second_namespace: []
""")
