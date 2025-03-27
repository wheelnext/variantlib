from variantlib import config as vconfig
from variantlib import meta as vmeta
from variantlib.api import KeyConfig
from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantMeta
from variantlib.api import get_variant_hashes_by_priority


def test_api_accessible():
    """Test that the API is accessible."""
    assert get_variant_hashes_by_priority is not None
    assert vconfig.KeyConfig is KeyConfig
    assert vconfig.ProviderConfig is ProviderConfig
    assert vmeta.VariantDescription is VariantDescription
    assert vmeta.VariantMeta is VariantMeta


def test_get_variant_hashes_by_priority():
    # TODO
    assert True
