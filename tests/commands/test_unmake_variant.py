from __future__ import annotations

from pathlib import Path

import pytest
from variantlib.commands.main import main
from variantlib.constants import NULL_VARIANT_LABEL

from tests.utils import assert_zips_equal


@pytest.mark.parametrize(
    "filename",
    [
        f"test_package-0-py3-none-any-{NULL_VARIANT_LABEL}.whl",
        "test_package-0-py3-none-any-5d8be4b9.whl",
        "test_package-0-py3-none-any-60567bd9.whl",
        "test_package-0-py3-none-any-fbe82642.whl",
        "test_package-0-py3-none-any-foo.whl",
        "test_package-0-py3-none-any-bar.whl",
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
            f"tests/artifacts/test-package/dist/{filename}",
            "-o",
            str(tmp_path),
        ]
    )
    assert_zips_equal(
        Path("tests/artifacts/test-package/dist/test_package-0-py3-none-any.whl"),
        tmp_path / "test_package-0-py3-none-any.whl",
    )
