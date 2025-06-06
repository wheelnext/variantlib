from __future__ import annotations

import logging
import sys
from enum import IntEnum
from functools import cache
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

import platformdirs

from variantlib import __package_name__
from variantlib.constants import CONFIG_FILENAME
from variantlib.errors import ConfigurationError
from variantlib.models.configuration import VariantConfiguration as ConfigurationModel
from variantlib.utils import classproperty

if TYPE_CHECKING:
    from collections.abc import Callable

    from variantlib.protocols import VariantFeatureName
    from variantlib.protocols import VariantFeatureValue
    from variantlib.protocols import VariantNamespace

if sys.version_info >= (3, 11):
    from typing import Self

    import tomllib
else:
    import tomli as tomllib
    from typing_extensions import Self

logger = logging.getLogger(__name__)


class ConfigEnvironments(IntEnum):
    LOCAL = 1
    VIRTUALENV = 2
    USER = 3
    GLOBAL = 4


@cache
def get_configuration_files() -> dict[ConfigEnvironments, Path]:
    return {
        ConfigEnvironments.LOCAL: Path.cwd() / CONFIG_FILENAME,
        ConfigEnvironments.VIRTUALENV: Path(sys.prefix) / CONFIG_FILENAME,
        ConfigEnvironments.USER: (
            platformdirs.user_config_path(
                __package_name__, appauthor=False, roaming=True
            )
            / CONFIG_FILENAME
        ),
        ConfigEnvironments.GLOBAL: (
            platformdirs.site_config_path(__package_name__, appauthor=False)
            / CONFIG_FILENAME
        ),
    }


R = TypeVar("R")


def check_initialized(func: Callable[..., R]) -> Callable[..., R]:
    @wraps(func)
    def wrapper(cls: type[VariantConfiguration], *args: Any, **kwargs: Any) -> R:
        if cls._config is None:
            cls._config = cls.get_config()

        return func(cls, *args, **kwargs)

    return wrapper


class VariantConfiguration:
    _config: ConfigurationModel | None = None

    def __new__(cls, *args: Any, **kwargs: dict[str, Any]) -> Self:
        raise RuntimeError(f"Cannot instantiate {cls.__name__}")

    @classmethod
    def reset(cls) -> None:
        """Reset the configuration to its initial state"""
        cls._config = None

    @classmethod
    def get_config_file(cls) -> Path:
        """Get the configuration file path"""
        config_files = get_configuration_files()
        for config_name in ConfigEnvironments:
            if (cfg_f := config_files[config_name]).exists():
                return cfg_f

        raise FileNotFoundError("No configuration file found.")

    @classmethod
    def get_config_from_file(cls, config_file: Path) -> ConfigurationModel:
        """Load the configuration from a file"""
        with config_file.open("rb") as f:
            try:
                config = tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                raise ConfigurationError from e

        return ConfigurationModel.from_toml_config(**config)

    @classmethod
    def get_config(cls) -> ConfigurationModel:
        """Load the configuration from the configuration files"""
        try:
            return cls.get_config_from_file(cls.get_config_file())
        except FileNotFoundError:
            # No user-configuration file found
            return ConfigurationModel.default()

    @classproperty
    @check_initialized
    def namespace_priorities(cls) -> list[VariantNamespace]:  # noqa: N805
        return cls._config.namespace_priorities  # type: ignore[union-attr]

    @classproperty
    @check_initialized
    def feature_priorities(cls) -> dict[VariantNamespace, list[VariantFeatureName]]:  # noqa: N805
        return cls._config.feature_priorities  # type: ignore[union-attr]

    @classproperty
    @check_initialized
    def property_priorities(
        cls,  # noqa: N805
    ) -> dict[VariantNamespace, dict[VariantFeatureName, list[VariantFeatureValue]]]:
        return cls._config.property_priorities  # type: ignore[union-attr]
