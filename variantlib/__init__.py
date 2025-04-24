from __future__ import annotations

import importlib.metadata
import logging

__package_name__ = "variantlib"

try:
    __version__ = importlib.metadata.version(__package_name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

logger = logging.getLogger(__package_name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
