from collections.abc import Generator

import pytest

from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import ListPluginLoader


@pytest.fixture(scope="session")
def mocked_plugin_apis() -> list[str]:
    return [
        "tests.mocked_plugins:MockedPluginA",
        "tests.mocked_plugins:MockedPluginB",
        "tests.mocked_plugins:MockedPluginC",
    ]


@pytest.fixture(scope="session")
def mocked_plugin_loader(
    mocked_plugin_apis: list[str],
) -> Generator[BasePluginLoader]:
    with ListPluginLoader(mocked_plugin_apis) as loader:
        yield loader
