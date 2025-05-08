from collections.abc import Callable
from collections.abc import Generator
from contextlib import _GeneratorContextManager
from contextlib import contextmanager

import pytest

from variantlib.plugins.loader import CLIPluginLoader
from variantlib.plugins.py_envs import ExternalNonIsolatedPythonEnv


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
) -> Callable[[], _GeneratorContextManager[CLIPluginLoader]]:
    @contextmanager
    def ctx() -> Generator[CLIPluginLoader]:
        with ExternalNonIsolatedPythonEnv() as py_ctx:  # noqa: SIM117
            with CLIPluginLoader(
                plugin_apis=mocked_plugin_apis, python_ctx=py_ctx
            ) as loader:
                yield loader

    return ctx
