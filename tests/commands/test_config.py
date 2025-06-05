from __future__ import annotations

from pathlib import Path

import pytest

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
    monkeypatch: pytest.MonkeyPatch,
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
