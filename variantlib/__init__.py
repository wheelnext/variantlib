from __future__ import annotations

import importlib.metadata

from variantlib import logger  # noqa: F401

try:
    __version__ = importlib.metadata.version("variantlib")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"
