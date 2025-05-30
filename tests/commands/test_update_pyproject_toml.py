from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import tomlkit

from variantlib.commands.main import main

if TYPE_CHECKING:
    from pathlib import Path


def test_update_pyproject_toml(
    mocked_entry_points: None,
    tmp_path: Path,
) -> None:
    pyproject_toml = tmp_path / "pyproject.toml"

    toml_data: dict[str, Any] = {
        "variant": {
            "default-priorities": {
                "namespace": [
                    "test_namespace",
                    "foo",
                ],
                "feature": ["foo::bar"],
                "property": ["foo::bar::baz"],
            },
            "providers": {
                "test_namespace": {
                    "requires": ["frobnicate", "barnicate"],
                    "enable-if": "python_version >= '3.11'",
                    "plugin-api": "wrong_value",
                },
                "foo": {
                    "plugin-api": "foo",
                },
            },
        },
    }
    pyproject_toml.write_text(tomlkit.dumps(toml_data))

    # '-a test_namespace' should update plugin-api
    main(["update-pyproject-toml", "-f", str(pyproject_toml), "-a", "test_namespace"])
    toml_data["variant"]["providers"]["test_namespace"]["plugin-api"] = (
        "tests.mocked_plugins:MockedPluginA"
    )
    assert tomlkit.loads(pyproject_toml.read_text()).value == toml_data

    # '-a second_namespace' should add second_namespace
    main(["update-pyproject-toml", "-f", str(pyproject_toml), "-a", "second_namespace"])
    toml_data["variant"]["default-priorities"]["namespace"].append("second_namespace")
    toml_data["variant"]["providers"]["second_namespace"] = {
        "plugin-api": "tests.mocked_plugins:MockedPluginB",
        "requires": [],
    }
    assert tomlkit.loads(pyproject_toml.read_text()).value == toml_data

    # '-d test_namespace -a test_namespace' should readd it
    main(
        [
            "update-pyproject-toml",
            "-f",
            str(pyproject_toml),
            "-d",
            "test_namespace",
            "-a",
            "test_namespace",
        ]
    )
    del toml_data["variant"]["providers"]["test_namespace"]["enable-if"]
    toml_data["variant"]["providers"]["test_namespace"]["requires"].clear()
    toml_data["variant"]["default-priorities"]["namespace"].remove("test_namespace")
    toml_data["variant"]["default-priorities"]["namespace"].append("test_namespace")
    assert tomlkit.loads(pyproject_toml.read_text()).value == toml_data

    # '-d foo' should remove it
    main(["update-pyproject-toml", "-f", str(pyproject_toml), "-d", "foo"])
    del toml_data["variant"]["providers"]["foo"]
    toml_data["variant"]["default-priorities"]["namespace"].remove("foo")
    assert tomlkit.loads(pyproject_toml.read_text()).value == toml_data
