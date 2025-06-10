from __future__ import annotations

from pathlib import Path

import pytest

from tests.utils import assert_zips_equal
from variantlib.commands.main import main


@pytest.mark.parametrize(
    "filename",
    [
        "test_package-0-py3-none-any-00000000.whl",
        "test_package-0-py3-none-any-5d8be4b9.whl",
    ],
)
def test_unmake_variant(
    filename: str,
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
        Path("tests/artifacts/test_package-0-py3-none-any.whl"),
        tmp_path / "test_package-0-py3-none-any.whl",
    )
