from __future__ import annotations

import logging
import sys
from enum import IntEnum
from functools import cache
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import TypeVar

import platformdirs

from variantlib import errors
from variantlib.constants import CONFIG_FILENAME
from variantlib.models.configuration import VariantConfiguration as ConfigurationModel
from variantlib.utils import classproperty

if TYPE_CHECKING:
    from variantlib.models.variant import VariantFeature
    from variantlib.models.variant import VariantProperty

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
            Path(
                platformdirs.user_config_dir(
                    "variantlib", appauthor=False, roaming=True
                )
            )
            / CONFIG_FILENAME
        ),
        ConfigEnvironments.GLOBAL: (
            Path(platformdirs.site_config_dir("variantlib", appauthor=False))
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
    def get_config(cls) -> ConfigurationModel:
        """Load the configuration from the configuration files"""
        # TODO: Read namespace priority configuration
        # TODO: Read namespace-feature prority configuration
        # TODO: Read namespace-feature-value prority configuration
        config_files = get_configuration_files()

        for config_name in ConfigEnvironments:
            if (cfg_f := config_files[config_name]).exists():
                logger.info("Loading configuration file: %s", config_files[config_name])
                with cfg_f.open("rb") as f:
                    try:
                        config = tomllib.load(f)
                    except tomllib.TOMLDecodeError as e:
                        raise errors.ConfigurationError from e

                return ConfigurationModel.from_toml_config(**config)

        # No user-configuration file found
        return ConfigurationModel.default()

    @classproperty
    @check_initialized
    def namespaces_priority(cls) -> list[str]:  # noqa: N805
        return cls._config.namespaces_priority  # type: ignore[union-attr]

    @classproperty
    @check_initialized
    def features_priority(cls) -> list[VariantFeature]:  # noqa: N805
        return cls._config.features_priority  # type: ignore[union-attr]

    @classproperty
    @check_initialized
    def property_priority(cls) -> list[VariantProperty]:  # noqa: N805
        return cls._config.property_priority  # type: ignore[union-attr]
