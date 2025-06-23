from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

    from variantlib.protocols import VariantFeatureConfigType
    from variantlib.protocols import VariantPropertyType


namespace = "module_namespace"


def get_all_configs(
    known_properties: Collection[VariantPropertyType] = (),
) -> list[VariantFeatureConfigType]:
    return [Namespace(name="feature", values=["a", "b"])]


def get_supported_configs(
    known_properties: Collection[VariantPropertyType] = (),
) -> list[VariantFeatureConfigType]:
    return []
