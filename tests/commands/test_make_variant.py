from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.utils import assert_zips_equal
from variantlib.commands.main import main
from variantlib.validators.base import ValidationError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def pyproject_toml(
    tmp_path: Path,
) -> Path:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("""
[variant.default-priorities]
namespace = ["installable_plugin"]

[variant.providers.installable_plugin]
requires = [
    "test-plugin-package @ file:///dev/null",
]
plugin-api = "test_plugin_package"
""")
    return pyproject_toml


def test_make_null_variant(
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    main(
        [
            "make-variant",
            "-f",
            "tests/artifacts/test_package-0-py3-none-any.whl",
            "-o",
            str(tmp_path),
            "--pyproject-toml",
            str(pyproject_toml),
            "--null-variant",
        ]
    )
    assert_zips_equal(
        Path("tests/artifacts/test_package-0-py3-none-any-00000000.whl"),
        tmp_path / "test_package-0-py3-none-any-00000000.whl",
    )


@pytest.fixture
def mocked_plugin_installer(
    mocker: MockerFixture,
    test_plugin_package_req: str,
) -> None:
    mocker.patch(
        "variantlib.plugins.loader.PluginLoader._install_all_plugins",
        new=lambda self: self._install_all_plugins_from_reqs([test_plugin_package_req]),
    )


def test_make_variant(
    pyproject_toml: Path,
    tmp_path: Path,
    mocked_plugin_installer: None,
) -> None:
    main(
        [
            "make-variant",
            "-f",
            "tests/artifacts/test_package-0-py3-none-any.whl",
            "-o",
            str(tmp_path),
            "--pyproject-toml",
            str(pyproject_toml),
            "-p",
            "installable_plugin::feat1::val1c",
            "-p",
            "installable_plugin::feat2::val2b",
        ]
    )
    assert_zips_equal(
        Path("tests/artifacts/test_package-0-py3-none-any-5d8be4b9.whl"),
        tmp_path / "test_package-0-py3-none-any-5d8be4b9.whl",
    )


def test_make_variant_invalid(
    pyproject_toml: Path,
    tmp_path: Path,
    mocked_plugin_installer: None,
) -> None:
    with pytest.raises(ValidationError):
        main(
            [
                "make-variant",
                "-f",
                "tests/artifacts/test_package-0-py3-none-any.whl",
                "-o",
                str(tmp_path),
                "--pyproject-toml",
                str(pyproject_toml),
                "-p",
                "foo::bar::baz",
            ]
        )


def test_make_variant_no_validate(
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    main(
        [
            "make-variant",
            "-f",
            "tests/artifacts/test_package-0-py3-none-any.whl",
            "-o",
            str(tmp_path),
            "--pyproject-toml",
            str(pyproject_toml),
            "--skip-plugin-validation",
            "-p",
            "installable_plugin::feat1::val1c",
            "-p",
            "installable_plugin::feat2::val2b",
        ]
    )
    assert_zips_equal(
        Path("tests/artifacts/test_package-0-py3-none-any-5d8be4b9.whl"),
        tmp_path / "test_package-0-py3-none-any-5d8be4b9.whl",
    )
