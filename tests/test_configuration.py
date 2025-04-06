from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import platformdirs

from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import VariantConfiguration
from variantlib.configuration import get_configuration_files
from variantlib.constants import CONFIG_FILENAME
from variantlib.models.configuration import VariantConfiguration as ConfigurationModel
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty


def dict_to_toml(d: dict, indent: int = 0) -> str:
    lines = []
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"\n{' ' * indent}[{key}]")
            lines.append(dict_to_toml(value, indent))
        elif isinstance(value, list):
            items = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in value)
            lines.append(f"{' ' * indent}{key} = [{items}]")
        elif isinstance(value, str):
            lines.append(f'{" " * indent}{key} = "{value}"')
        else:
            raise TypeError(f"Unsupported type for key '{key}': {type(value)}")
    return "\n".join(lines)


def test_reset():
    VariantConfiguration._config = ConfigurationModel.default()  # noqa: SLF001
    assert VariantConfiguration._config is not None  # noqa: SLF001
    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001


def test_get_configuration_files():
    config_files = get_configuration_files()
    assert config_files[ConfigEnvironments.LOCAL] == Path.cwd() / CONFIG_FILENAME
    assert (
        config_files[ConfigEnvironments.VIRTUALENV]
        == Path(sys.prefix) / CONFIG_FILENAME
    )
    assert (
        config_files[ConfigEnvironments.USER]
        == Path(
            platformdirs.user_config_dir("variantlib", appauthor=False, roaming=True)
        )
        / CONFIG_FILENAME
    )
    assert (
        config_files[ConfigEnvironments.GLOBAL]
        == Path(platformdirs.site_config_dir("variantlib", appauthor=False))
        / CONFIG_FILENAME
    )


@patch("variantlib.configuration.get_configuration_files")
def test_get_config_no_files(mock_get_config_files):
    mock_get_config_files.return_value = {
        ConfigEnvironments.LOCAL: Path("/nonexistent/config.toml"),
        ConfigEnvironments.VIRTUALENV: Path("/nonexistent/config.toml"),
        ConfigEnvironments.USER: Path("/nonexistent/config.toml"),
        ConfigEnvironments.GLOBAL: Path("/nonexistent/config.toml"),
    }
    config = VariantConfiguration.get_config()
    assert config == ConfigurationModel.default()


@patch("variantlib.configuration.get_configuration_files")
def test_get_default_config_with_no_file(mock_get_config_files):
    mock_get_config_files.return_value = {
        ConfigEnvironments.LOCAL: Path("/nonexistent/config.toml"),
        ConfigEnvironments.VIRTUALENV: Path("/nonexistent/config.toml"),
        ConfigEnvironments.USER: Path("/nonexistent/config.toml"),
        ConfigEnvironments.GLOBAL: Path("/nonexistent/config.toml"),
    }
    config = VariantConfiguration.get_config()
    assert config == ConfigurationModel.default()


@patch("variantlib.configuration.get_configuration_files")
def test_get_config_from_file(mock_get_config_files):
    data = {
        "property_priority": [
            "fictional_hw::architecture::mother",
            "fictional_tech::risk_exposure::25",
        ],
        "features_priority": [
            "fictional_hw::architecture",
            "fictional_tech::risk_exposure",
            "simd_x86_64::feature3",
        ],
        "namespaces_priority": [
            "fictional_hw",
            "fictional_tech",
            "simd_x86_64",
            "non_existent_provider",
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml") as temp_file:
        temp_file.write(dict_to_toml(data))
        temp_file.flush()

        def _get_config_files() -> dict[ConfigEnvironments, Path]:
            return {
                ConfigEnvironments.LOCAL: Path("/nonexistent/config.toml"),
                ConfigEnvironments.VIRTUALENV: Path("/nonexistent/config.toml"),
                ConfigEnvironments.USER: Path("/nonexistent/config.toml"),
                ConfigEnvironments.GLOBAL: Path("/nonexistent/config.toml"),
            }

        features_priority = [
            VariantFeature.from_str(f) for f in data["features_priority"]
        ]

        property_priority = [
            VariantProperty.from_str(f) for f in data["property_priority"]
        ]

        for env in ConfigEnvironments:
            config_files = _get_config_files()
            config_files[env] = Path(temp_file.name)
            mock_get_config_files.return_value = config_files

            config = VariantConfiguration.get_config()
            assert config.features_priority == features_priority
            assert config.property_priority == property_priority
            assert config.namespaces_priority == data["namespaces_priority"]


def test_class_properties_with_default():
    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001
    assert VariantConfiguration.namespaces_priority == []
    assert VariantConfiguration._config is not None  # noqa: SLF001

    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001
    assert VariantConfiguration.features_priority == []
    assert VariantConfiguration._config is not None  # noqa: SLF001

    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001
    assert VariantConfiguration.property_priority == []
    assert VariantConfiguration._config is not None  # noqa: SLF001
