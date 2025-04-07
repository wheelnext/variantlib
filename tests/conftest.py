import pytest

from variantlib.loader import PluginLoader


@pytest.fixture(autouse=True)
def flush_caches():
    yield
    PluginLoader.flush_cache()
