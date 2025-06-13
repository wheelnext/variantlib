from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import tomlkit

from variantlib.commands.main import main
from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_FEATURE_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROPERTY_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY

if TYPE_CHECKING:
    from pathlib import Path


def test_update_pyproject_toml(
    mocked_entry_points: None,
    tmp_path: Path,
) -> None:
    pyproject_toml = tmp_path / "pyproject.toml"

    toml_data: dict[str, Any] = {
        PYPROJECT_TOML_TOP_KEY: {
            VARIANT_INFO_DEFAULT_PRIO_KEY: {
                VARIANT_INFO_NAMESPACE_KEY: [
                    "test_namespace",
                    "foo",
                ],
                VARIANT_INFO_FEATURE_KEY: ["foo::bar"],
                VARIANT_INFO_PROPERTY_KEY: ["foo::bar::baz"],
            },
            VARIANT_INFO_PROVIDER_DATA_KEY: {
                "test_namespace": {
                    VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["frobnicate", "barnicate"],
                    VARIANT_INFO_PROVIDER_ENABLE_IF_KEY: "python_version >= '3.11'",
                    VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "wrong_value",
                },
                "foo": {
                    VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "foo",
                },
            },
        },
    }
    pyproject_toml.write_text(tomlkit.dumps(toml_data))

    # '-a test_namespace' should update plugin-api
    main(["update-pyproject-toml", "-f", str(pyproject_toml), "-a", "test_namespace"])
    toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_PROVIDER_DATA_KEY]["test_namespace"][
        VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
    ] = "tests.mocked_plugins:MockedPluginA"
    assert tomlkit.loads(pyproject_toml.read_text()).value == toml_data

    # '-a second_namespace' should add second_namespace
    main(["update-pyproject-toml", "-f", str(pyproject_toml), "-a", "second_namespace"])
    toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_DEFAULT_PRIO_KEY][
        VARIANT_INFO_NAMESPACE_KEY
    ].append("second_namespace")
    toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_PROVIDER_DATA_KEY][
        "second_namespace"
    ] = {
        "plugin-api": "tests.mocked_plugins:MockedPluginB",
        VARIANT_INFO_PROVIDER_REQUIRES_KEY: [],
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
    del toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_PROVIDER_DATA_KEY][
        "test_namespace"
    ][VARIANT_INFO_PROVIDER_ENABLE_IF_KEY]
    toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_PROVIDER_DATA_KEY]["test_namespace"][
        VARIANT_INFO_PROVIDER_REQUIRES_KEY
    ].clear()
    toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_DEFAULT_PRIO_KEY][
        VARIANT_INFO_NAMESPACE_KEY
    ].remove("test_namespace")
    toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_DEFAULT_PRIO_KEY][
        VARIANT_INFO_NAMESPACE_KEY
    ].append("test_namespace")

    assert tomlkit.loads(pyproject_toml.read_text()).value == toml_data

    # '-d foo' should remove it
    main(["update-pyproject-toml", "-f", str(pyproject_toml), "-d", "foo"])
    del toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_PROVIDER_DATA_KEY]["foo"]
    toml_data[PYPROJECT_TOML_TOP_KEY][VARIANT_INFO_DEFAULT_PRIO_KEY][
        VARIANT_INFO_NAMESPACE_KEY
    ].remove("foo")
    assert tomlkit.loads(pyproject_toml.read_text()).value == toml_data
