import os
from collections.abc import Generator
from pathlib import Path

import pytest

from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import ListPluginLoader

# Set PYTHONPATH to ensure that tests can find plugins
os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent)


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
