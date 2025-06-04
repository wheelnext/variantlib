import os
from collections.abc import Generator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from tests.mocked_plugins import MockedEntryPoint
from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import ListPluginLoader

# Set PYTHONPATH to ensure that tests can find plugins
os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent)

pytest.register_assert_rewrite("tests.utils")


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


@pytest.fixture
def mocked_entry_points(
    mocker: MockerFixture,
    mocked_plugin_apis: list[str],
) -> None:
    mocker.patch("variantlib.plugins.loader.entry_points")().select.return_value = [
        MockedEntryPoint("test", "tests.mocked_plugins:MockedPluginA"),
        MockedEntryPoint("second", "tests.mocked_plugins:MockedPluginB"),
        MockedEntryPoint("third", "tests.mocked_plugins:MockedPluginC"),
    ]


@pytest.fixture(scope="session")
def test_plugin_package_req() -> str:
    wheel_path = Path(
        "tests/artifacts/test-plugin-package/dist/test_plugin_package-0-py3-none-any.whl"
    )
    assert wheel_path.exists(), f"Test plugin package wheel not found: {wheel_path}"
    return f"test-plugin-package @ file://{wheel_path.absolute().as_posix()}"
