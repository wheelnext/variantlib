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
