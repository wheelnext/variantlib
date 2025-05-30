from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.utils import assert_zips_equal
from variantlib.commands.main import main

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "filename",
    [
        "test_plugin_package-0-py3-none-any-00000000.whl",
        "test_plugin_package-0-py3-none-any-5d8be4b9.whl",
        "test_plugin_package-0-py3-none-any-ac31c899.whl",
    ],
)
def test_unmake_variant(
    filename: str,
    test_plugin_package_wheel_path: Path,
    tmp_path: Path,
) -> None:
    main(
        [
            "unmake-variant",
            "-f",
            f"tests/artifacts/{filename}",
            "-o",
            str(tmp_path),
        ]
    )
    assert_zips_equal(
        test_plugin_package_wheel_path,
        tmp_path / "test_plugin_package-0-py3-none-any.whl",
        replace_plugin_path=test_plugin_package_wheel_path.parent,
    )
