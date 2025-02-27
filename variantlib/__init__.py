import importlib.metadata

from variantlib import logger  # noqa: F401
from variantlib.constants import VARIANT_HASH_LEN  # noqa: F401

__version__ = importlib.metadata.version("variantlib")
