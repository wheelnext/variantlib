from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantProperty
from variantlib.validators.base import validate_type

if TYPE_CHECKING:
    from collections.abc import Generator


def get_combinations(
    provider_cfgs: list[ProviderConfig], namespace_priorities: list[str]
) -> Generator[VariantDescription]:
    """Generate all possible combinations of `VariantProperty` given a list of
    `ProviderConfig`.

    NOTE: This function respects some basic ordering and priority."""

    assert isinstance(provider_cfgs, (list, tuple))
    assert len(provider_cfgs) > 0
    assert all(isinstance(config, ProviderConfig) for config in provider_cfgs)

    validate_type(provider_cfgs, list[ProviderConfig])
    validate_type(namespace_priorities, list[str])

    provider_cfgs_dict = {
        provider_cfg.namespace: provider_cfg for provider_cfg in provider_cfgs
    }

    all_properties = [
        (provider_cfgs_dict[namespace].namespace, feature_cfg.name, feature_cfg.values)
        for namespace in namespace_priorities
        for feature_cfg in provider_cfgs_dict[namespace].configs
        if namespace in provider_cfgs_dict
    ]

    def yield_all_values(
        remaining_properties: list[tuple[str, str, list[str]]],
    ) -> Generator[list[VariantProperty]]:
        namespace, feature, values = remaining_properties[0]
        for value in values:
            for start in range(1, len(remaining_properties)):
                for other_values in yield_all_values(remaining_properties[start:]):
                    yield [VariantProperty(namespace, feature, value), *other_values]
            yield [VariantProperty(namespace, feature, value)]

    for start in range(len(all_properties)):
        for properties in yield_all_values(all_properties[start:]):
            yield VariantDescription(properties)

    # Finish by the null variant
    yield VariantDescription()


def assert_zips_equal(
    ref_path: Path,
    new_path: Path,
) -> None:
    with ZipFile(ref_path) as ref_zip, ZipFile(new_path) as new_zip:
        assert set(ref_zip.namelist()) == set(new_zip.namelist())
        for filepath in ref_zip.namelist():
            filename = Path(filepath).name

            if filename == "RECORD":
                # ignore RECORD file, checksums will differ depending on plugin paths
                continue

            if filename == "variant.json":
                with (
                    ref_zip.open(filepath) as ref_file,
                    new_zip.open(filepath) as new_file,
                ):
                    assert json.loads(new_file.read().decode()) == json.loads(
                        ref_file.read().decode()
                    )

            else:
                with (
                    ref_zip.open(filepath) as ref_file,
                    new_zip.open(filepath) as new_file,
                ):
                    assert new_file.readlines() == ref_file.readlines()
