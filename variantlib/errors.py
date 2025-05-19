from variantlib.validators.base import ValidationError

__all__ = [
    "ConfigurationError",
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


class ConfigurationError(ValueError):
    pass
