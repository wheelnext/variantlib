import pytest

from tests.mocked_plugins import MockedEntryPoint
from tests.mocked_plugins import MockedPluginA
from tests.mocked_plugins import MockedPluginB
from tests.mocked_plugins import MockedPluginC
from variantlib.loader import PluginLoader


@pytest.fixture(autouse=True)
def flush_caches():
    yield
    PluginLoader.flush_cache()


@pytest.fixture
def mocked_plugin_loader(session_mocker):
    session_mocker.patch("variantlib.loader.entry_points")().select.return_value = [
        MockedEntryPoint(
            name="test_namespace",
            value="tests.test_plugins:MockedPluginA",
            plugin=MockedPluginA,
        ),
        MockedEntryPoint(
            name="second_namespace",
            value="tests.test_plugins:MockedPluginB",
            plugin=MockedPluginB,
        ),
        MockedEntryPoint(
            name="incompatible_namespace",
            value="tests.test_plugins:MockedPluginC",
            plugin=MockedPluginC,
        ),
    ]

    return PluginLoader
