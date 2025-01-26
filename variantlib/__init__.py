import importlib.metadata
import logging
import sys

from variantlib.constants import VARIANT_HASH_LEN  # noqa: F401

__version__ = importlib.metadata.version("variantlib")


logger = logging.getLogger("variantlib")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)
