from collections.abc import Callable
from collections.abc import Generator
from contextlib import _GeneratorContextManager
from contextlib import contextmanager

import pytest

from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import ManualPluginLoader


@pytest.fixture(scope="session")
def mocked_plugin_apis() -> list[str]:
    return [
        "tests.mocked_plugins:MockedPluginA",
        "tests.mocked_plugins:MockedPluginB",
        "tests.mocked_plugins:MockedPluginC",
    ]


@pytest.fixture(scope="session")
def mocked_plugin_loader_ctx(
    mocked_plugin_apis: list[str],
) -> Callable[[], _GeneratorContextManager[BasePluginLoader]]:
    @contextmanager
    def ctx() -> Generator[BasePluginLoader]:
        loader = ManualPluginLoader()
        for plugin_api in mocked_plugin_apis:
            loader.load_plugin(plugin_api)
        yield loader

    return ctx
