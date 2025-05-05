import pytest

from variantlib.loader import PluginLoader


@pytest.fixture(autouse=True)
def flush_caches():
    yield
    PluginLoader.flush_cache()


@pytest.fixture
def mocked_plugin_loader(session_mocker):
    PluginLoader.load_plugin("tests.mocked_plugins:MockedPluginA")
    PluginLoader.load_plugin("tests.mocked_plugins:MockedPluginB")
    PluginLoader.load_plugin("tests.mocked_plugins:MockedPluginC")

    return PluginLoader
