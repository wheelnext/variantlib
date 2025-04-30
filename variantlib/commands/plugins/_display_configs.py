from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from variantlib.models.variant import VariantProperty

if TYPE_CHECKING:
    from variantlib.models.provider import ProviderConfig

logger = logging.getLogger(__name__)


def display_configs(
    provider_configs: list[ProviderConfig],
    namespace_filter: str | None,
    feature_filter: str | None,
    sort_vprops: bool = False,
) -> None:
    vprops = []
    for provider_cfg in provider_configs:
        if namespace_filter is not None and namespace_filter != provider_cfg.namespace:
            continue

        for feature in provider_cfg.configs:
            if feature_filter is not None and feature_filter != feature.name:
                continue

            for value in feature.values:
                vprops.append(  # noqa: PERF401
                    VariantProperty(
                        provider_cfg.namespace, feature.name, value
                    ).to_str()
                )

    for vprop in sorted(vprops) if sort_vprops else vprops:
        sys.stdout.write(f"{vprop}\n")
