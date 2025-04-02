from __future__ import annotations

from string import ascii_lowercase
from typing import TYPE_CHECKING

import pytest

from tests.test_plugins import mocked_plugin_loader  # noqa: F401
from variantlib.api import KeyConfig
from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantMeta
from variantlib.api import VariantValidationResult
from variantlib.api import get_variant_hashes_by_priority
from variantlib.api import validate_variant
from variantlib.models import provider as pconfig
from variantlib.models import variant as vconfig

if TYPE_CHECKING:
    from variantlib.loader import PluginLoader


def test_api_accessible():
    """Test that the API is accessible."""
    assert get_variant_hashes_by_priority is not None
    assert pconfig.KeyConfig is KeyConfig
    assert pconfig.ProviderConfig is ProviderConfig
    assert vconfig.VariantDescription is VariantDescription
    assert vconfig.VariantMeta is VariantMeta


def test_get_variant_hashes_by_priority():
    # TODO
    assert True


@pytest.mark.parametrize(
    ("bools", "valid", "valid_strict"),
    [
        ((True,), True, True),
        ((None,), True, False),
        ((False,), False, False),
        ((True, True, True), True, True),
        ((True, True, None), True, False),
        ((None, None, None), True, False),
        ((True, True, False), False, False),
        ((True, None, False), False, False),
        ((None, None, False), False, False),
        # corner case: the base variant is also valid
        ((), True, True),
    ],
)
def test_validation_result_is_valid(
    bools: tuple[bool, ...], valid: bool, valid_strict: bool
):
    res = VariantValidationResult(
        {
            VariantMeta(
                ascii_lowercase[i], ascii_lowercase[i], ascii_lowercase[i]
            ): var_res
            for i, var_res in enumerate(bools)
        }
    )
    assert res.is_valid() == valid
    assert res.is_valid(allow_unknown_plugins=False) == valid_strict


def test_validate_variant(mocked_plugin_loader: type[PluginLoader]):  # noqa: F811
    res = validate_variant(
        VariantDescription(
            [
                VariantMeta("test_plugin", "key1", "val1d"),
                VariantMeta("test_plugin", "key2", "val2d"),
                VariantMeta("test_plugin", "key3", "val3a"),
                VariantMeta("second_plugin", "key3", "val3a"),
                VariantMeta("incompatible_plugin", "flag1", "on"),
                VariantMeta("incompatible_plugin", "flag2", "off"),
                VariantMeta("incompatible_plugin", "flag5", "on"),
                VariantMeta("missing_plugin", "key", "val"),
                VariantMeta("private", "build_type", "debug"),
            ]
        )
    )

    assert res == VariantValidationResult(
        {
            VariantMeta(namespace="test_plugin", key="key1", value="val1d"): True,
            VariantMeta(namespace="test_plugin", key="key2", value="val2d"): False,
            VariantMeta(namespace="test_plugin", key="key3", value="val3a"): False,
            VariantMeta(namespace="second_plugin", key="key3", value="val3a"): True,
            VariantMeta(namespace="incompatible_plugin", key="flag1", value="on"): True,
            VariantMeta(
                namespace="incompatible_plugin", key="flag2", value="off"
            ): False,
            VariantMeta(
                namespace="incompatible_plugin", key="flag5", value="on"
            ): False,
            VariantMeta(namespace="missing_plugin", key="key", value="val"): None,
            VariantMeta(namespace="private", key="build_type", value="debug"): None,
        }
    )
    assert not res.is_valid()
