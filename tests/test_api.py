from __future__ import annotations

from string import ascii_lowercase
from typing import TYPE_CHECKING

import pytest

from tests.test_plugins import mocked_plugin_loader  # noqa: F401
from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantFeatureConfig
from variantlib.api import VariantProperty
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
    assert pconfig.VariantFeatureConfig is VariantFeatureConfig
    assert pconfig.ProviderConfig is ProviderConfig
    assert vconfig.VariantDescription is VariantDescription
    assert vconfig.VariantProperty is VariantProperty


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
            VariantProperty(
                ascii_lowercase[i], ascii_lowercase[i], ascii_lowercase[i]
            ): var_res
            for i, var_res in enumerate(bools)
        }
    )
    assert res.is_valid() == valid
    assert res.is_valid(allow_unknown_plugins=False) == valid_strict


def test_validation_result_properties():
    res = VariantValidationResult(
        {
            VariantProperty("blas", "variant", "mkl"): True,
            VariantProperty("cuda", "runtime", "12.0"): None,
            VariantProperty("blas", "invariant", "lkm"): False,
            VariantProperty("x86_64", "baseline", "v10"): False,
            VariantProperty("orange", "juice", "good"): None,
        }
    )

    assert res.invalid_properties == [
        VariantProperty("blas", "invariant", "lkm"),
        VariantProperty("x86_64", "baseline", "v10"),
    ]
    assert res.unknown_properties == [
        VariantProperty("cuda", "runtime", "12.0"),
        VariantProperty("orange", "juice", "good"),
    ]


def test_validate_variant(mocked_plugin_loader: type[PluginLoader]):  # noqa: F811
    res = validate_variant(
        VariantDescription(
            [
                VariantProperty("test_plugin", "name1", "val1d"),
                VariantProperty("test_plugin", "name2", "val2d"),
                VariantProperty("test_plugin", "name3", "val3a"),
                VariantProperty("second_plugin", "name3", "val3a"),
                VariantProperty("incompatible_plugin", "flag1", "on"),
                VariantProperty("incompatible_plugin", "flag2", "off"),
                VariantProperty("incompatible_plugin", "flag5", "on"),
                VariantProperty("missing_plugin", "name", "val"),
                VariantProperty("private", "build_type", "debug"),
            ]
        )
    )

    assert res == VariantValidationResult(
        {
            VariantProperty("test_plugin", "name1", "val1d"): True,
            VariantProperty("test_plugin", "name2", "val2d"): False,
            VariantProperty("test_plugin", "name3", "val3a"): False,
            VariantProperty("second_plugin", "name3", "val3a"): True,
            VariantProperty("incompatible_plugin", "flag1", "on"): True,
            VariantProperty("incompatible_plugin", "flag2", "off"): False,
            VariantProperty("incompatible_plugin", "flag5", "on"): False,
            VariantProperty("missing_plugin", "name", "val"): None,
            VariantProperty("private", "build_type", "debug"): None,
        }
    )
    assert not res.is_valid()
