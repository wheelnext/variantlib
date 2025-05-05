import pytest

from variantlib.loader import PluginLoader


@pytest.fixture(scope="session")
def mocked_plugin_loader():
    loader = PluginLoader()
    loader.load_plugin("tests.mocked_plugins:MockedPluginA")
    loader.load_plugin("tests.mocked_plugins:MockedPluginB")
    loader.load_plugin("tests.mocked_plugins:MockedPluginC")
    return loader
