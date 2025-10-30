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
{
  "test_namespace": [
    {
      "name": "name1",
      "values": [
        "val1a",
        "val1b",
        "val1c",
        "val1d"
      ],
      "multi_value": false
    },
    {
      "name": "name2",
      "values": [
        "val2a",
        "val2b",
        "val2c"
      ],
      "multi_value": true
    }
  ],
  "second_namespace": [
    {
      "name": "name3",
      "values": [
        "val3a",
        "val3b",
        "val3c"
      ],
      "multi_value": false
    }
  ],
  "incompatible_namespace": [
    {
      "name": "flag1",
      "values": [
        "on"
      ],
      "multi_value": false
    },
    {
      "name": "flag2",
      "values": [
        "on"
      ],
      "multi_value": false
    },
    {
      "name": "flag3",
      "values": [
        "on"
      ],
      "multi_value": false
    },
    {
      "name": "flag4",
      "values": [
        "on"
      ],
      "multi_value": false
    }
  ]
}\
""")


def test_plugins_get_all_configs_filter_namespace(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--all", "-n", "second_namespace"])
    assert capsys.readouterr().out == snapshot("""\
{
  "second_namespace": [
    {
      "name": "name3",
      "values": [
        "val3a",
        "val3b",
        "val3c"
      ],
      "multi_value": false
    }
  ]
}\
""")


def test_plugins_get_all_configs_filter_feature(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--all", "-f", "name1"])
    assert capsys.readouterr().out == snapshot("""\
{
  "test_namespace": [
    {
      "name": "name1",
      "values": [
        "val1a",
        "val1b",
        "val1c",
        "val1d"
      ],
      "multi_value": false
    }
  ],
  "second_namespace": [],
  "incompatible_namespace": []
}\
""")


def test_plugins_get_supported_configs(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--supported"])
    assert capsys.readouterr().out == snapshot("""\
{
  "test_namespace": [
    {
      "name": "name1",
      "values": [
        "val1a",
        "val1b"
      ],
      "multi_value": false
    },
    {
      "name": "name2",
      "values": [
        "val2a",
        "val2b",
        "val2c"
      ],
      "multi_value": true
    }
  ],
  "second_namespace": [
    {
      "name": "name3",
      "values": [
        "val3a"
      ],
      "multi_value": false
    }
  ]
}\
""")


def test_plugins_get_supported_configs_filter_namespace(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--supported", "-n", "second_namespace"])
    assert capsys.readouterr().out == snapshot("""\
{
  "second_namespace": [
    {
      "name": "name3",
      "values": [
        "val3a"
      ],
      "multi_value": false
    }
  ]
}\
""")


def test_plugins_get_supported_configs_filter_feature(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["plugins", "get-configs", "--supported", "-f", "name1"])
    assert capsys.readouterr().out == snapshot("""\
{
  "test_namespace": [
    {
      "name": "name1",
      "values": [
        "val1a",
        "val1b"
      ],
      "multi_value": false
    }
  ],
  "second_namespace": []
}\
""")
