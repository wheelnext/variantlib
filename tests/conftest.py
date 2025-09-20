import os
from collections.abc import Generator
from pathlib import Path

import pytest
from hypothesis import Verbosity
from hypothesis import settings
from pytest_mock import MockerFixture
from variantlib.plugins.loader import BasePluginLoader
from variantlib.plugins.loader import ListPluginLoader

from tests.mocked_plugins import MockedEntryPoint

# Set PYTHONPATH to ensure that tests can find plugins
os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent)

pytest.register_assert_rewrite("tests.utils")

settings.register_profile("fast", max_examples=1)
settings.register_profile("debug", max_examples=1, verbosity=Verbosity.verbose)
settings.load_profile(
    os.getenv("HYPOTHESIS_PROFILE", "ci" if "CI" in os.environ else "default")
)


MOCKED_PLUGIN_APIS = [
    "tests.mocked_plugins:MockedPluginA",
    "tests.mocked_plugins:MockedPluginB",
    "tests.mocked_plugins:MockedPluginC",
]


@pytest.fixture(scope="session")
def mocked_plugin_loader() -> Generator[BasePluginLoader]:
    with ListPluginLoader(MOCKED_PLUGIN_APIS) as loader:
        yield loader


@pytest.fixture
def mocked_entry_points(
    mocker: MockerFixture,
) -> None:
    mocker.patch("variantlib.plugins.loader.entry_points")().select.return_value = [
        MockedEntryPoint("test", "tests.mocked_plugins:MockedPluginA"),
        MockedEntryPoint("second", "tests.mocked_plugins:MockedPluginB"),
        MockedEntryPoint("third", "tests.mocked_plugins:MockedPluginC"),
    ]


@pytest.fixture(scope="session")
def test_artifact_path() -> Path:
    dir_path = Path("tests/artifacts/")
    if not dir_path.exists() or not dir_path.is_dir():
        raise FileNotFoundError(f"Test artifacts directory not found: `{dir_path}`")
    return dir_path


@pytest.fixture(scope="session")
def test_plugin_package_path(test_artifact_path: Path) -> Path:
    wheel_path = (
        test_artifact_path
        / "test-plugin-package/dist/test_plugin_package-0-py3-none-any.whl"
    )

    if not wheel_path.exists() or not wheel_path.is_file():
        raise FileNotFoundError(f"Test plugin package wheel not found: `{wheel_path}`")

    return wheel_path


@pytest.fixture(scope="session")
def test_plugin_package_req(test_plugin_package_path: Path) -> str:
    return (
        f"test-plugin-package @ file://{test_plugin_package_path.absolute().as_posix()}"
    )
