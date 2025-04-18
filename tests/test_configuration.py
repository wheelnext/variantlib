from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import platformdirs
import tomli_w

from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import VariantConfiguration
from variantlib.configuration import get_configuration_files
from variantlib.constants import CONFIG_FILENAME
from variantlib.models.configuration import VariantConfiguration as ConfigurationModel
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    import pytest


def test_reset():
    VariantConfiguration._config = ConfigurationModel.default()  # noqa: SLF001
    assert VariantConfiguration._config is not None  # noqa: SLF001
    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001


def test_get_configuration_files():
    get_configuration_files.cache_clear()
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


def test_get_configuration_files_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "prefix", "/virtual-env")
    monkeypatch.setenv("XDG_CONFIG_DIRS", "/system-config:/second-config")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/config-home")

    get_configuration_files.cache_clear()
    assert get_configuration_files() == {
        ConfigEnvironments.LOCAL: tmp_path / "variants.toml",
        ConfigEnvironments.VIRTUALENV: Path("/virtual-env/variants.toml"),
        ConfigEnvironments.USER: Path("/config-home/variantlib/variants.toml"),
        ConfigEnvironments.GLOBAL: Path("/system-config/variantlib/variants.toml"),
    }


def test_get_configuration_files_unix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "prefix", "/virtual-env")
    monkeypatch.setenv("HOME", "/home/mocked-user")
    monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    get_configuration_files.cache_clear()
    assert get_configuration_files() == {
        ConfigEnvironments.LOCAL: tmp_path / "variants.toml",
        ConfigEnvironments.VIRTUALENV: Path("/virtual-env/variants.toml"),
        ConfigEnvironments.USER: Path(
            "/home/mocked-user/.config/variantlib/variants.toml"
        ),
        ConfigEnvironments.GLOBAL: Path("/etc/xdg/variantlib/variants.toml"),
    }


def test_get_default_config_with_no_file(mocker):
    mocker.patch("variantlib.configuration.get_configuration_files").return_value = {
        ConfigEnvironments.LOCAL: Path("/nonexistent/config.toml"),
        ConfigEnvironments.VIRTUALENV: Path("/nonexistent/config.toml"),
        ConfigEnvironments.USER: Path("/nonexistent/config.toml"),
        ConfigEnvironments.GLOBAL: Path("/nonexistent/config.toml"),
    }
    config = VariantConfiguration.get_config()
    assert config == ConfigurationModel.default()


def test_get_config_from_file(mocker, tmp_path: Path):
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
    config_path = Path(tmp_path) / "config.toml"
    with config_path.open("wb") as config_file:
        tomli_w.dump(data, config_file)

    def _get_config_files() -> dict[ConfigEnvironments, Path]:
        return {
            ConfigEnvironments.LOCAL: Path("/nonexistent/config.toml"),
            ConfigEnvironments.VIRTUALENV: Path("/nonexistent/config.toml"),
            ConfigEnvironments.USER: Path("/nonexistent/config.toml"),
            ConfigEnvironments.GLOBAL: Path("/nonexistent/config.toml"),
        }

    features_priority = [VariantFeature.from_str(f) for f in data["features_priority"]]

    property_priority = [VariantProperty.from_str(f) for f in data["property_priority"]]

    for env in ConfigEnvironments:
        config_files = _get_config_files()
        config_files[env] = config_path
        mocker.patch(
            "variantlib.configuration.get_configuration_files"
        ).return_value = config_files

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
