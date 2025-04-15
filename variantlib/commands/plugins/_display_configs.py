from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from variantlib.models.provider import ProviderConfig

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def display_configs(
    provider_configs: list[ProviderConfig],
    namespace_filter: str | None,
    feature_filter: str | None,
) -> None:
    for provider_cfg in provider_configs:
        if namespace_filter is not None and namespace_filter != provider_cfg.namespace:
            continue

        for feature in provider_cfg.configs:
            if feature_filter is not None and feature_filter != feature.name:
                continue

            for value in feature.values:
                vprop = VariantProperty(provider_cfg.namespace, feature.name, value)
                sys.stdout.write(f"{vprop.to_str()}\n")
