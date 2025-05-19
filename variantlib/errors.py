from variantlib.validators.base import ValidationError

__all__ = [
    "ConfigurationError",
    "InvalidVariantEnvSpecError",
    "NoPluginFoundError",
    "PluginError",
    "PluginMissingError",
    "ValidationError",
]


class PluginError(RuntimeError):
    """Incorrect plugin implementation"""


class PluginMissingError(RuntimeError):
    """A required plugin is missing"""


class NoPluginFoundError(RuntimeError):
    """A required plugin is missing"""


class InvalidVariantEnvSpecError(ValueError):
    """Environment specifier for variants is invalid"""


class ConfigurationError(ValueError):
    pass
