from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import platformdirs
import pytest
import tomlkit

from variantlib import __package_name__
from variantlib.configuration import ConfigEnvironments
from variantlib.configuration import VariantConfiguration
from variantlib.configuration import get_configuration_files
from variantlib.constants import CONFIG_FILENAME
from variantlib.models.configuration import VariantConfiguration as ConfigurationModel
from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_reset() -> None:
    VariantConfiguration._config = ConfigurationModel.default()  # noqa: SLF001
    assert VariantConfiguration._config is not None  # noqa: SLF001
    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001


def test_get_configuration_files() -> None:
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
            platformdirs.user_config_dir(
                __package_name__, appauthor=False, roaming=True
            )
        )
        / CONFIG_FILENAME
    )
    assert (
        config_files[ConfigEnvironments.GLOBAL]
        == Path(platformdirs.site_config_dir(__package_name__, appauthor=False))
        / CONFIG_FILENAME
    )


@pytest.mark.skipif(sys.platform in ("darwin", "win32"), reason="unix-specific")
def test_get_configuration_files_xdg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


@pytest.mark.skipif(sys.platform in ("darwin", "win32"), reason="unix-specific")
def test_get_configuration_files_unix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific")
def test_get_configuration_files_macos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "prefix", "/virtual-env")
    monkeypatch.setenv("HOME", "/home/mocked-user")

    get_configuration_files.cache_clear()
    assert get_configuration_files() == {
        ConfigEnvironments.LOCAL: tmp_path / "variants.toml",
        ConfigEnvironments.VIRTUALENV: Path("/virtual-env/variants.toml"),
        ConfigEnvironments.USER: Path(
            "/home/mocked-user/Library/Application Support/variantlib/variants.toml"
        ),
        ConfigEnvironments.GLOBAL: Path(
            "/Library/Application Support/variantlib/variants.toml"
        ),
    }


def test_get_default_config_with_no_file(mocker: MockerFixture) -> None:
    mocker.patch("variantlib.configuration.get_configuration_files").return_value = {
        ConfigEnvironments.LOCAL: Path("/nonexistent/config.toml"),
        ConfigEnvironments.VIRTUALENV: Path("/nonexistent/config.toml"),
        ConfigEnvironments.USER: Path("/nonexistent/config.toml"),
        ConfigEnvironments.GLOBAL: Path("/nonexistent/config.toml"),
    }
    config = VariantConfiguration.get_config()
    assert config == ConfigurationModel.default()


def test_get_config_from_file(mocker: MockerFixture, tmp_path: Path) -> None:
    data = {
        "property_priorities": [
            "fictional_hw::architecture::mother",
            "fictional_tech::risk_exposure::25",
        ],
        "feature_priorities": {
            "fictional_hw": ["architecture"],
            "fictional_tech": ["risk_exposure"],
            "simd_x86_64": ["feature3"],
        },
        "namespace_priorities": [
            "fictional_hw",
            "fictional_tech",
            "simd_x86_64",
            "non_existent_provider",
        ],
    }
    config_path = Path(tmp_path) / "config.toml"
    with config_path.open("w") as config_file:
        tomlkit.dump(data, config_file)

    def _get_config_files() -> dict[ConfigEnvironments, Path]:
        return {
            ConfigEnvironments.LOCAL: Path("/nonexistent/config.toml"),
            ConfigEnvironments.VIRTUALENV: Path("/nonexistent/config.toml"),
            ConfigEnvironments.USER: Path("/nonexistent/config.toml"),
            ConfigEnvironments.GLOBAL: Path("/nonexistent/config.toml"),
        }

    property_priorities = [
        VariantProperty.from_str(f) for f in data["property_priorities"]
    ]

    for env in ConfigEnvironments:
        config_files = _get_config_files()
        config_files[env] = config_path
        mocker.patch(
            "variantlib.configuration.get_configuration_files"
        ).return_value = config_files

        config = VariantConfiguration.get_config()
        assert config.feature_priorities == data["feature_priorities"]
        assert config.property_priorities == property_priorities
        assert config.namespace_priorities == data["namespace_priorities"]


def test_class_properties_with_default(mocker: MockerFixture) -> None:
    mocker.patch(
        "variantlib.configuration.VariantConfiguration.get_config_file"
    ).side_effect = FileNotFoundError

    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001
    assert VariantConfiguration.namespace_priorities == []
    assert VariantConfiguration._config is not None  # noqa: SLF001

    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001
    assert VariantConfiguration.feature_priorities == {}
    assert VariantConfiguration._config is not None  # noqa: SLF001

    VariantConfiguration.reset()
    assert VariantConfiguration._config is None  # noqa: SLF001
    assert VariantConfiguration.property_priorities == []
    assert VariantConfiguration._config is not None  # noqa: SLF001
