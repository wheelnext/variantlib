from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from variantlib.protocols import VariantFeatureConfigType
    from variantlib.protocols import VariantPropertyType


namespace = "module_namespace"
dynamic = False


def get_all_configs(
    known_properties: frozenset[VariantPropertyType] | None,
) -> list[VariantFeatureConfigType]:
    assert known_properties is None
    return [Namespace(name="feature", values=["a", "b"])]


def get_supported_configs(
    known_properties: frozenset[VariantPropertyType] | None,
) -> list[VariantFeatureConfigType]:
    assert known_properties is None
    return []
