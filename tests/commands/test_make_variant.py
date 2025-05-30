from __future__ import annotations

from pathlib import Path

from tests.utils import assert_zips_equal
from variantlib.commands.main import main


def test_make_null_variant(
    test_plugin_package_wheel_path: Path,
    tmp_path: Path,
) -> None:
    main(
        [
            "make-variant",
            "-f",
            str(test_plugin_package_wheel_path),
            "-o",
            str(tmp_path),
            "--null-variant",
        ]
    )
    assert_zips_equal(
        Path("tests/artifacts/test_plugin_package-0-py3-none-any-00000000.whl"),
        tmp_path / "test_plugin_package-0-py3-none-any-00000000.whl",
    )


def test_make_variant(
    test_plugin_package_wheel_path: Path,
    test_plugin_package_req: str,
    tmp_path: Path,
) -> None:
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
    )
