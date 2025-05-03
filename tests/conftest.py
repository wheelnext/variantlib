import shutil
from pathlib import Path

import pytest
import tomlkit

from tests.mocked_plugins import MockedDistribution
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
            dist=MockedDistribution(name="test-plugin", version="1.2.3"),
            plugin=MockedPluginA,
        ),
        MockedEntryPoint(
            name="second_namespace",
            value="tests.test_plugins:MockedPluginB",
            dist=MockedDistribution(name="second-plugin", version="4.5.6"),
            plugin=MockedPluginB,
        ),
        MockedEntryPoint(
            name="incompatible_namespace",
            value="tests.test_plugins:MockedPluginC",
            plugin=MockedPluginC,
        ),
    ]

    return PluginLoader


def is_setuptools(package_path):
    if package_path.joinpath("setup.py").is_file():
        return True
    pyproject = package_path / "pyproject.toml"
    try:
        with pyproject.open("rb") as f:
            pp = tomlkit.load(f)
    except (FileNotFoundError, ValueError):
        return True
    return "setuptools" in pp.get("build-system", {}).get("build-backend", "setuptools")


@pytest.fixture
def packages_path() -> Path:
    return Path(__file__).parent / "packages"


def generate_package_path_fixture(package_name):
    @pytest.fixture
    def fixture(packages_path: Path, tmp_path: Path) -> str:
        package_path = packages_path / package_name
        if not is_setuptools(package_path):
            return str(package_path)

        new_path = tmp_path / package_name
        shutil.copytree(package_path, new_path)
        return str(new_path)

    return fixture


# Generate path fixtures dynamically.
package_dirs = Path(__file__).parent.joinpath("packages")
for package_dir in package_dirs.iterdir():
    package_name = package_dir.name
    normalized_name = package_name.replace("-", "_")
    fixture_name = f"package_{normalized_name}"
    globals()[fixture_name] = generate_package_path_fixture(package_name)
