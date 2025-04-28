from __future__ import annotations

import importlib.metadata

__package_name__ = "variantlib"

try:
    __version__ = importlib.metadata.version(__package_name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"
