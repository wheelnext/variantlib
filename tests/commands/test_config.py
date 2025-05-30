from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
import tomlkit

from variantlib.commands.main import main
from variantlib.configuration import get_configuration_files


@pytest.fixture
def config_toml(tmp_path: Path) -> Path:
    config_toml = tmp_path / "variants.toml"
    config_toml.write_text("""
feature_priorities = []
namespace_priorities = [
    "test_namespace",
    "incompatible_namespace",
    "second_namespace",
]
property_priorities = []
""")
    return config_toml


def test_config_list_paths(
    capsys: pytest.CaptureFixture[str],
) -> None:
    get_configuration_files.cache_clear()
    main(["config", "list-paths", "-v"])
    stdout = capsys.readouterr().out
    assert [x.split(":", 1)[0] for x in stdout.splitlines()] == [
        "LOCAL",
        "VIRTUALENV",
        "USER",
        "GLOBAL",
    ]
    assert stdout.startswith(f"LOCAL: {Path('variants.toml').absolute()}")


def test_config_show(
    config_toml: Path,
    monkeypatch: pytest.MonkeyPatcher,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(config_toml.parent)
    get_configuration_files.cache_clear()
    main(["config", "show"])
    assert (
        capsys.readouterr().out
        == f"""\
# This file has been sourced from: `{config_toml.absolute()}`

namespace_priorities = [
    "test_namespace",
    "incompatible_namespace",
    "second_namespace",
]

feature_priorities = []

property_priorities = []

"""
    )


def test_config_setup_defaults(
    config_toml: Path,
    mocked_entry_points: None,
    monkeypatch: pytest.MonkeyPatcher,
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("y\n"))
    main(["config", "setup", "--ui", "text", "-d", "-P", str(config_toml)])
    assert tomlkit.loads(config_toml.read_text()).value == {
        "feature_priorities": [],
        "namespace_priorities": [
            "incompatible_namespace",
            "second_namespace",
            "test_namespace",
        ],
        "property_priorities": [],
    }


def test_config_setup(
    mocked_entry_points: None,
    monkeypatch: pytest.MonkeyPatcher,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("\n3 2 1\n\n\ny\n"))
    main(["config", "setup", "--ui", "text", "-P", str(tmp_path / "config.toml")])
    assert tomlkit.loads((tmp_path / "config.toml").read_text()).value == {
        "feature_priorities": [],
        "namespace_priorities": [
            "test_namespace",
            "second_namespace",
            "incompatible_namespace",
        ],
        "property_priorities": [],
    }


def test_config_setup_all(
    mocked_entry_points: None,
    monkeypatch: pytest.MonkeyPatcher,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("\n3 2 1\ny\n2 3\ny\n4 1\ny\n"))
    main(["config", "setup", "--ui", "text", "-P", str(tmp_path / "config.toml")])
    assert tomlkit.loads((tmp_path / "config.toml").read_text()).value == {
        "feature_priorities": [
            "test_namespace :: name2",
            "second_namespace :: name3",
        ],
        "namespace_priorities": [
            "test_namespace",
            "second_namespace",
            "incompatible_namespace",
        ],
        "property_priorities": [
            "second_namespace :: name3 :: val3a",
            "test_namespace :: name2 :: val2a",
        ],
    }


def test_config_setup_defaults_no_save(
    mocked_entry_points: None,
    monkeypatch: pytest.MonkeyPatcher,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("n\n"))
    main(["config", "setup", "--ui", "text", "-d", "-P", str(tmp_path / "config.toml")])
    assert not (tmp_path / "config.toml").exists()


def test_config_setup_update(
    config_toml: Path,
    mocked_entry_points: None,
    monkeypatch: pytest.MonkeyPatcher,
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("\n3 2 1\n\n\ny\n"))
    main(["config", "setup", "--ui", "text", "-P", str(config_toml)])
    assert tomlkit.loads(config_toml.read_text()).value == {
        "feature_priorities": [],
        "namespace_priorities": [
            "test_namespace",
            "second_namespace",
            "incompatible_namespace",
        ],
        "property_priorities": [],
    }
