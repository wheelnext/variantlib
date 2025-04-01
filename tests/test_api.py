from __future__ import annotations

from variantlib.api import KeyConfig
from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantMeta
from variantlib.api import get_variant_hashes_by_priority
from variantlib.models import provider as pconfig
from variantlib.models import variant as vconfig


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
