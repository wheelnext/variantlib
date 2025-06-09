from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.protocols import VariantFeatureConfigType


namespace = "module_namespace"


def get_all_configs() -> list[VariantFeatureConfigType]:
    return [Namespace(name="feature", values=["a", "b"])]


def get_supported_configs() -> list[VariantFeatureConfigType]:
    return []
