class ValidationError(ValueError):
    pass


class PluginError(RuntimeError):
    """Incorrect plugin implementation"""


class PluginMissingError(RuntimeError):
    """A required plugin is missing"""


class InvalidVariantEnvSpecError(ValueError):
    pass
