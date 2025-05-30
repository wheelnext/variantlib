from __future__ import annotations

from pathlib import Path

import pytest

from tests.utils import assert_zips_equal
from variantlib.commands.main import main
from variantlib.validators.base import ValidationError


@pytest.fixture
def pyproject_toml(
    test_plugin_package_req: str,
    tmp_path: Path,
) -> Path:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(f"""
[variant.default-priorities]
namespace = ["installable_plugin"]

[variant.providers.installable_plugin]
requires = [
    "{test_plugin_package_req}",
]
plugin-api = "test_plugin_package:TestPlugin"
""")
    return pyproject_toml


def test_make_null_variant(
    test_plugin_package_wheel_path: Path,
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    main(
        [
            "make-variant",
            "-f",
            str(test_plugin_package_wheel_path),
            "-o",
            str(tmp_path),
            "--pyproject-toml",
            str(pyproject_toml),
            "--null-variant",
        ]
    )
    assert_zips_equal(
        Path("tests/artifacts/test_plugin_package-0-py3-none-any-00000000.whl"),
        tmp_path / "test_plugin_package-0-py3-none-any-00000000.whl",
        replace_plugin_path=test_plugin_package_wheel_path.parent,
    )


def test_make_variant(
    test_plugin_package_wheel_path: Path,
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    main(
        [
            "make-variant",
            "-f",
            str(test_plugin_package_wheel_path),
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
        Path("tests/artifacts/test_plugin_package-0-py3-none-any-5d8be4b9.whl"),
        tmp_path / "test_plugin_package-0-py3-none-any-5d8be4b9.whl",
        replace_plugin_path=test_plugin_package_wheel_path.parent,
    )


def test_make_variant_invalid(
    test_plugin_package_wheel_path: Path,
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError):
        main(
            [
                "make-variant",
                "-f",
                str(test_plugin_package_wheel_path),
                "-o",
                str(tmp_path),
                "--pyproject-toml",
                str(pyproject_toml),
                "-p",
                "foo::bar::baz",
            ]
        )


def test_make_variant_no_validate(
    test_plugin_package_wheel_path: Path,
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    main(
        [
            "make-variant",
            "-f",
            str(test_plugin_package_wheel_path),
            "-o",
            str(tmp_path),
            "--pyproject-toml",
            str(pyproject_toml),
            "--skip-plugin-validation",
            "-p",
            "foo::bar::baz",
        ]
    )
    assert_zips_equal(
        Path("tests/artifacts/test_plugin_package-0-py3-none-any-ac31c899.whl"),
        tmp_path / "test_plugin_package-0-py3-none-any-ac31c899.whl",
        replace_plugin_path=test_plugin_package_wheel_path.parent,
    )
